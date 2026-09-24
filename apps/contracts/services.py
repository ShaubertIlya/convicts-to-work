import hashlib
import json
import secrets
from calendar import monthrange
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.accounts.models import User
from apps.applications.models import CandidateProposal, JobApplication
from apps.audit.services import record_event
from apps.core.identifiers import parse_unique_uuid_list
from apps.notifications.services import notify_users
from apps.organizations.snapshots import build_organization_snapshot

from .biometry import BiometryClient, BiometryError
from .models import (
    BiometricSignatureAttempt,
    ContractSequence,
    ContractSignature,
    EmploymentContract,
)


def _notify_contract_parties(contract, title_ru, title_kk, exclude_user=None):
    users = User.objects.filter(
        Q(organization=contract.organization, role=User.Role.BUSINESS_ADMIN)
        | Q(
            organization__kind="ENBEK",
            role__in=[User.Role.ENBEK_MANAGER, User.Role.ENBEK_EXECUTOR],
        )
    )
    if exclude_user:
        users = users.exclude(pk=exclude_user.pk)
    notify_users(
        users, title_ru=title_ru, title_kk=title_kk,
        related_type="contract", related_id=contract.id,
    )


def _next_number() -> str:
    year = timezone.localdate().year
    sequence, _ = ContractSequence.objects.select_for_update().get_or_create(year=year)
    sequence.last_value += 1
    sequence.save(update_fields=["last_value"])
    return f"TD-{year}-{sequence.last_value:06d}"


def _annual_end(starts_on):
    year = starts_on.year + 1
    day = min(starts_on.day, monthrange(year, starts_on.month)[1])
    return starts_on.replace(year=year, day=day)


@transaction.atomic
def create_contracts(
    application: JobApplication, candidate_ids: list, starts_on, ends_on, actor=None
):
    candidate_ids = parse_unique_uuid_list(candidate_ids)
    application = (
        JobApplication.objects.select_for_update(of=("self",))
        .select_related("organization__bank")
        .get(pk=application.pk)
    )
    if application.status not in {
        JobApplication.Status.SCREENING,
        JobApplication.Status.CONTRACTING,
    }:
        raise ValidationError("Заявка ещё не находится на этапе договоров.")
    candidates = list(
        CandidateProposal.objects.select_for_update()
        .select_related("prisoner")
        .filter(application=application, id__in=candidate_ids)
    )
    if len(candidates) != len(candidate_ids):
        raise ValidationError("Передан некорректный список кандидатов.")
    if any(c.status != CandidateProposal.Status.READY_FOR_CONTRACT for c in candidates):
        raise ValidationError("Договор доступен только после двух успешных обследований.")
    if ends_on <= starts_on:
        raise ValidationError("Дата окончания должна быть позже даты начала.")
    if application.duration_months != 12 or ends_on != _annual_end(starts_on):
        raise ValidationError("Срок договора должен составлять ровно 12 месяцев.")
    contracts = []
    # A contract must use the legally relevant requisites captured when the
    # application was submitted, not values later edited in the company profile.
    organization_snapshot = application.organization_snapshot or build_organization_snapshot(
        application.organization
    )
    for candidate in candidates:
        contracts.append(
            EmploymentContract.objects.create(
                number=_next_number(),
                application=application,
                candidate=candidate,
                prisoner=candidate.prisoner,
                organization=application.organization,
                organization_snapshot=organization_snapshot,
                starts_on=starts_on,
                ends_on=ends_on,
            )
        )
        candidate.status = CandidateProposal.Status.CONTRACT_CREATED
        candidate.save(update_fields=["status", "updated_at"])
    application.status = JobApplication.Status.CONTRACTING
    application.save(update_fields=["status", "updated_at"])
    record_event(actor, "contracts.created", application, {"count": len(contracts)})
    notify_users(
        User.objects.filter(organization=application.organization, role=User.Role.BUSINESS_ADMIN),
        title_ru="Созданы трудовые договоры",
        title_kk="Еңбек шарттары жасалды",
        related_type="application",
        related_id=application.id,
    )
    return contracts


def _state_digest(state: str) -> str:
    return hashlib.sha256(state.encode()).hexdigest()


def biometry_contract_number(verification_id: str, state: str) -> str | None:
    if not verification_id or not state:
        return None
    return (
        BiometricSignatureAttempt.objects.filter(
            verification_id=verification_id,
            state_digest=_state_digest(state),
        )
        .values_list("contract__number", flat=True)
        .first()
    )


def _contract_digest(contract: EmploymentContract) -> str:
    payload = {
        "id": str(contract.id),
        "number": contract.number,
        "application": str(contract.application_id),
        "prisoner": str(contract.prisoner_id),
        "organization": str(contract.organization_id),
        "organization_snapshot": contract.organization_snapshot,
        "starts_on": contract.starts_on.isoformat(),
        "ends_on": contract.ends_on.isoformat(),
        "document_hash": contract.document_hash,
        "document_version": contract.document_version,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _ensure_document_integrity(contract: EmploymentContract) -> None:
    if not contract.document or not contract.document_hash:
        raise ValidationError("Перед подписанием загрузите PDF-документ договора.")
    digest = hashlib.sha256()
    with contract.document.open("rb") as document:
        for chunk in document.chunks():
            digest.update(chunk)
    if digest.hexdigest() != contract.document_hash:
        raise ValidationError("Файл договора изменился после фиксации документа.")


@transaction.atomic
def upload_contract_document(contract: EmploymentContract, document, actor) -> EmploymentContract:
    contract = EmploymentContract.objects.select_for_update().get(pk=contract.pk)
    if actor.role not in {User.Role.ENBEK_EXECUTOR, User.Role.ENBEK_MANAGER}:
        raise ValidationError("Только сотрудник Еңбек может приложить договор.")
    if contract.signatures.exists():
        raise ValidationError("Нельзя заменить документ после первой подписи.")
    if contract.biometric_attempts.filter(
        status=BiometricSignatureAttempt.Status.PENDING, expires_at__gt=timezone.now()
    ).exists():
        raise ValidationError("Дождитесь завершения текущей биометрической попытки.")
    if not document or not document.name.lower().endswith(".pdf"):
        raise ValidationError("Приложите договор в формате PDF.")
    if document.size > 10 * 1024 * 1024:
        raise ValidationError("Размер договора не должен превышать 10 МБ.")
    try:
        reader = PdfReader(document, strict=True)
        if reader.is_encrypted:
            raise ValidationError("Загрузите PDF без пароля и шифрования.")
        if not reader.pages:
            raise ValidationError("PDF-документ не содержит страниц.")
    except (PdfReadError, ValueError, OSError) as exc:
        raise ValidationError("Файл не является корректным PDF-документом.") from exc
    document.seek(0)
    digest = hashlib.sha256()
    for chunk in document.chunks():
        digest.update(chunk)
    document.seek(0)
    if contract.document:
        contract.document_version += 1
    contract.document.save(
        f"{contract.number}-v{contract.document_version}.pdf", document, save=False
    )
    contract.document_hash = digest.hexdigest()
    contract.save(update_fields=["document", "document_hash", "document_version", "updated_at"])
    record_event(actor, "contract.document_uploaded", contract, {"sha256": contract.document_hash})
    notify_users(
        User.objects.filter(organization=contract.organization, role=User.Role.BUSINESS_ADMIN),
        title_ru="Договор готов к ознакомлению",
        title_kk="Шарт танысуға дайын",
        related_type="contract",
        related_id=contract.id,
    )
    return contract


@transaction.atomic
def start_prisoner_signature(contract: EmploymentContract, actor, acknowledged=False, client=None):
    contract = (
        EmploymentContract.objects.select_for_update()
        .select_related("prisoner")
        .get(pk=contract.pk)
    )
    if contract.signatures.filter(party=ContractSignature.Party.PRISONER).exists():
        raise ValidationError("Осуждённый уже подписал договор.")
    _ensure_document_integrity(contract)
    if acknowledged is not True:
        raise ValidationError("Подтвердите, что осуждённый ознакомился с PDF договора.")
    now = timezone.now()
    contract.biometric_attempts.filter(
        status=BiometricSignatureAttempt.Status.PENDING, expires_at__lte=now
    ).update(
        status=BiometricSignatureAttempt.Status.EXPIRED,
        completed_at=now,
        updated_at=now,
    )
    pending = contract.biometric_attempts.filter(
        status=BiometricSignatureAttempt.Status.PENDING, expires_at__gt=now
    ).exists()
    if pending:
        raise ValidationError("По договору уже запущена биометрическая проверка.")
    if not contract.prisoner.photo:
        raise ValidationError("В карточке осуждённого отсутствует эталонное фото.")
    client = client or BiometryClient()
    state = secrets.token_urlsafe(32)
    with contract.prisoner.photo.open("rb") as reference_file:
        try:
            response = client.start(reference_file, state)
        except BiometryError as exc:
            raise ValidationError(str(exc)) from exc
    verification_id = response.get("verification_id")
    if not verification_id:
        raise ValidationError("Сервис биометрии не вернул идентификатор проверки.")
    expires_in = min(max(int(response.get("expires_in", 120)), 1), 600)
    BiometricSignatureAttempt.objects.create(
        contract=contract,
        initiated_by=actor,
        state_digest=_state_digest(state),
        verification_id=verification_id,
        contract_version=contract.document_version,
        contract_digest=_contract_digest(contract),
        consent_acknowledged_at=timezone.now(),
        expires_at=timezone.now() + timedelta(seconds=expires_in),
    )
    return {
        "verification_id": verification_id,
        "redirect_url": client.frontend_url(verification_id),
    }


def _refresh_contract_status(contract: EmploymentContract):
    parties = set(contract.signatures.values_list("party", flat=True))
    required = {
        ContractSignature.Party.PRISONER,
        ContractSignature.Party.ENBEK_MANAGER,
        ContractSignature.Party.BUSINESS_ADMIN,
    }
    contract.status = (
        EmploymentContract.Status.ACTIVE
        if parties == required
        else EmploymentContract.Status.PARTIALLY_SIGNED
    )
    contract.save(update_fields=["status", "updated_at"])
    if contract.status == EmploymentContract.Status.ACTIVE:
        application = contract.application
        has_unsigned = application.contracts.exclude(
            status__in=[EmploymentContract.Status.ACTIVE, EmploymentContract.Status.EXPIRED]
        ).exists()
        finished_candidate_statuses = [
            CandidateProposal.Status.BUSINESS_REJECTED,
            CandidateProposal.Status.ENBEK_REJECTED,
            CandidateProposal.Status.MEDICAL_FAILED,
            CandidateProposal.Status.PSYCHOLOGICAL_FAILED,
            CandidateProposal.Status.CONTRACT_CREATED,
        ]
        has_unfinished_candidates = application.candidates.exclude(
            status__in=finished_candidate_statuses
        ).exists()
        if not has_unsigned and not has_unfinished_candidates:
            application.status = JobApplication.Status.COMPLETED
            application.save(update_fields=["status", "updated_at"])


def complete_biometry(verification_id: str, state: str, outcome: str, client=None):
    failure = None
    with transaction.atomic():
        try:
            attempt = (
                BiometricSignatureAttempt.objects.select_for_update()
                .select_related("contract")
                .get(state_digest=_state_digest(state), verification_id=verification_id)
            )
        except BiometricSignatureAttempt.DoesNotExist as exc:
            raise ValidationError("Биометрическая попытка не найдена.") from exc
        if attempt.status == BiometricSignatureAttempt.Status.VERIFIED:
            if attempt.contract.signatures.filter(party=ContractSignature.Party.PRISONER).exists():
                return attempt.contract
            raise ValidationError("Результат биометрии не согласован с подписью договора.")
        if attempt.status != BiometricSignatureAttempt.Status.PENDING:
            raise ValidationError("Биометрическая попытка уже завершена.")
        if outcome not in {"success", "failed", "expired"}:
            raise ValidationError("Неизвестный результат биометрической проверки.")
        if not attempt.consent_acknowledged_at:
            raise ValidationError("Не зафиксировано ознакомление с PDF договора.")
        if (
            attempt.contract_version != attempt.contract.document_version
            or attempt.contract_digest != _contract_digest(attempt.contract)
        ):
            raise ValidationError("Договор изменился после запуска биометрии.")
        _ensure_document_integrity(attempt.contract)
        if attempt.expires_at <= timezone.now() or outcome == "expired":
            attempt.status = BiometricSignatureAttempt.Status.EXPIRED
            failure = "Срок биометрической попытки истёк."
        elif outcome != "success":
            attempt.status = BiometricSignatureAttempt.Status.FAILED
            failure = "Биометрическая проверка не пройдена."
        if failure:
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=["status", "completed_at", "updated_at"])
        else:
            client = client or BiometryClient()
            try:
                result = client.consume(verification_id)
            except BiometryError as exc:
                raise ValidationError(str(exc)) from exc
            if result.get("verified") is not True or result.get("status") != "CONSUMED":
                raise ValidationError("Сервис биометрии не подтвердил одноразовый результат.")
            signed_at = timezone.now()
            ContractSignature.objects.create(
                contract=attempt.contract,
                party=ContractSignature.Party.PRISONER,
                method=ContractSignature.Method.BIOMETRY,
                signed_by=attempt.initiated_by,
                signed_at=signed_at,
                evidence={
                    "verification_id": verification_id,
                    "status": "CONSUMED",
                    "consent_acknowledged_at": attempt.consent_acknowledged_at.isoformat(),
                    "document_hash": attempt.contract.document_hash,
                    "document_version": attempt.contract.document_version,
                },
            )
            attempt.status = BiometricSignatureAttempt.Status.VERIFIED
            attempt.completed_at = signed_at
            attempt.save(update_fields=["status", "completed_at", "updated_at"])
            _refresh_contract_status(attempt.contract)
            record_event(attempt.initiated_by, "contract.prisoner_signed", attempt.contract)
            _notify_contract_parties(
                attempt.contract, "Осуждённый подписал договор",
                "Сотталған адам шартқа қол қойды",
            )
            return attempt.contract
    raise ValidationError(failure)


@transaction.atomic
def button_sign(contract: EmploymentContract, actor):
    contract = EmploymentContract.objects.select_for_update().get(pk=contract.pk)
    _ensure_document_integrity(contract)
    if not contract.signatures.filter(party=ContractSignature.Party.PRISONER).exists():
        raise ValidationError("Сначала договор должен подписать осуждённый.")
    party_by_role = {
        User.Role.ENBEK_MANAGER: ContractSignature.Party.ENBEK_MANAGER,
        User.Role.BUSINESS_ADMIN: ContractSignature.Party.BUSINESS_ADMIN,
    }
    party = party_by_role.get(actor.role)
    if not party:
        raise ValidationError("У вашей роли нет права подписывать договор.")
    wrong_business = (
        party == ContractSignature.Party.BUSINESS_ADMIN
        and actor.organization_id != contract.organization_id
    )
    if wrong_business:
        raise ValidationError("Договор относится к другой организации.")
    if contract.signatures.filter(party=party).exists():
        raise ValidationError("Эта сторона уже подписала договор.")
    ContractSignature.objects.create(
        contract=contract,
        party=party,
        method=ContractSignature.Method.BUTTON,
        signed_by=actor,
        signed_at=timezone.now(),
        evidence={
            "document_hash": contract.document_hash,
            "document_version": contract.document_version,
        },
    )
    _refresh_contract_status(contract)
    record_event(actor, "contract.party_signed", contract, {"party": party})
    _notify_contract_parties(
        contract, "Новая подпись по договору", "Шартқа жаңа қол қойылды", actor,
    )
    return contract
