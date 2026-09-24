from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.core.identifiers import parse_unique_uuid_list
from apps.notifications.services import notify_users
from apps.organizations.snapshots import build_organization_snapshot

from .models import CandidateProposal, JobApplication, Screening


def _notify_business(application, title_ru, title_kk):
    notify_users(
        User.objects.filter(organization=application.organization, role=User.Role.BUSINESS_ADMIN),
        title_ru=title_ru,
        title_kk=title_kk,
        related_type="application",
        related_id=application.id,
    )


def _notify_enbek(application, roles, title_ru, title_kk):
    notify_users(
        User.objects.filter(role__in=roles, organization__kind="ENBEK"),
        title_ru=title_ru,
        title_kk=title_kk,
        related_type="application",
        related_id=application.id,
    )


@transaction.atomic
def submit_application(application: JobApplication, actor=None) -> JobApplication:
    application = JobApplication.objects.select_for_update().get(pk=application.pk)
    if application.status != JobApplication.Status.DRAFT:
        raise ValidationError("Подать можно только черновик заявки.")
    application.status = JobApplication.Status.SUBMITTED
    application.organization_snapshot = build_organization_snapshot(application.organization)
    application.save(update_fields=["status", "organization_snapshot", "updated_at"])
    record_event(actor or application.created_by, "application.submitted", application)
    _notify_enbek(
        application,
        [User.Role.ENBEK_EXECUTOR],
        "Поступила новая заявка",
        "Жаңа өтінім келіп түсті",
    )
    return application


@transaction.atomic
def withdraw_application(application: JobApplication, actor=None) -> JobApplication:
    application = JobApplication.objects.select_for_update().get(pk=application.pk)
    if application.status not in {JobApplication.Status.DRAFT, JobApplication.Status.SUBMITTED}:
        raise ValidationError("Заявку нельзя отозвать после ответа Еңбек.")
    application.status = JobApplication.Status.WITHDRAWN
    application.save(update_fields=["status", "updated_at"])
    record_event(actor or application.created_by, "application.withdrawn", application)
    _notify_enbek(
        application, [User.Role.ENBEK_EXECUTOR],
        "Заявка отозвана организацией", "Ұйым өтінімді қайтарып алды",
    )
    return application


@transaction.atomic
def propose_candidates(application: JobApplication, prisoner_ids: list, actor) -> JobApplication:
    prisoner_ids = parse_unique_uuid_list(prisoner_ids)
    application = (
        JobApplication.objects.select_for_update().select_related("skill").get(pk=application.pk)
    )
    if application.status != JobApplication.Status.SUBMITTED:
        raise ValidationError("Кандидатов можно предложить только по поданной заявке.")
    if len(prisoner_ids) > application.quantity:
        raise ValidationError("Нельзя предложить больше кандидатов, чем указано в заявке.")

    from apps.prisoners.models import Prisoner

    prisoners = list(
        Prisoner.objects.filter(id__in=prisoner_ids, is_available=True).prefetch_related("skills")
    )
    if len(prisoners) != len(prisoner_ids):
        raise ValidationError("Один или несколько кандидатов недоступны.")
    if application.skill_requirement == JobApplication.SkillRequirement.REQUIRED:
        invalid = [
            prisoner.id
            for prisoner in prisoners
            if application.skill_id not in {skill.id for skill in prisoner.skills.all()}
        ]
        if invalid:
            raise ValidationError("Для этой заявки можно предложить только кандидатов с навыком.")

    CandidateProposal.objects.bulk_create(
        [
            CandidateProposal(application=application, prisoner=prisoner, proposed_by=actor)
            for prisoner in prisoners
        ]
    )
    application.status = JobApplication.Status.PROPOSED
    application.save(update_fields=["status", "updated_at"])
    record_event(actor, "application.candidates_proposed", application)
    _notify_business(application, "Кандидаты подобраны", "Үміткерлер іріктелді")
    return application


@transaction.atomic
def business_respond(
    application: JobApplication, accepted_ids: list, comment: str = "", actor=None
) -> JobApplication:
    accepted_ids = parse_unique_uuid_list(accepted_ids, allow_empty=True)
    application = JobApplication.objects.select_for_update().get(pk=application.pk)
    if application.status != JobApplication.Status.PROPOSED:
        raise ValidationError("Ответ МСБ сейчас не ожидается.")
    proposals = list(application.candidates.select_for_update())
    valid_ids = {item.id for item in proposals}
    accepted = set(accepted_ids)
    if not accepted.issubset(valid_ids):
        raise ValidationError("Выбран кандидат, не относящийся к заявке.")
    for proposal in proposals:
        proposal.status = (
            CandidateProposal.Status.BUSINESS_ACCEPTED
            if proposal.id in accepted
            else CandidateProposal.Status.BUSINESS_REJECTED
        )
    CandidateProposal.objects.bulk_update(proposals, ["status", "updated_at"])
    application.business_comment = comment
    application.status = (
        JobApplication.Status.BUSINESS_RESPONDED
        if accepted
        else JobApplication.Status.REJECTED_BUSINESS
    )
    application.save(update_fields=["business_comment", "status", "updated_at"])
    record_event(actor or application.created_by, "application.business_responded", application)
    _notify_enbek(
        application,
        [User.Role.ENBEK_EXECUTOR, User.Role.ENBEK_MANAGER],
        "МСБ ответил по кандидатам",
        "Бизнес үміткерлер бойынша жауап берді",
    )
    return application


@transaction.atomic
def enbek_decide(
    application: JobApplication, approved: bool, comment: str = "", actor=None
) -> JobApplication:
    application = JobApplication.objects.select_for_update().get(pk=application.pk)
    if application.status != JobApplication.Status.BUSINESS_RESPONDED:
        raise ValidationError("Решение Еңбек сейчас не ожидается.")
    selected = list(
        application.candidates.select_for_update().filter(
            status=CandidateProposal.Status.BUSINESS_ACCEPTED
        )
    )
    for candidate in selected:
        candidate.status = (
            CandidateProposal.Status.ENBEK_APPROVED
            if approved
            else CandidateProposal.Status.ENBEK_REJECTED
        )
    CandidateProposal.objects.bulk_update(selected, ["status", "updated_at"])
    application.enbek_comment = comment
    application.status = (
        JobApplication.Status.APPROVED if approved else JobApplication.Status.REJECTED_ENBEK
    )
    application.save(update_fields=["enbek_comment", "status", "updated_at"])
    record_event(actor, "application.enbek_decided", application, {"approved": approved})
    _notify_business(
        application,
        "Еңбек согласовал заявку" if approved else "Еңбек отклонил заявку",
        "Еңбек өтінімді келісті" if approved else "Еңбек өтінімді қабылдамады",
    )
    return application


@transaction.atomic
def send_to_screening(candidate: CandidateProposal, kind: str, actor=None) -> Screening:
    candidate = (
        CandidateProposal.objects.select_for_update()
        .select_related("application")
        .get(pk=candidate.pk)
    )
    if kind == Screening.Kind.MEDICAL:
        allowed_status = CandidateProposal.Status.ENBEK_APPROVED
        pending_status = CandidateProposal.Status.MEDICAL_PENDING
    elif kind == Screening.Kind.PSYCHOLOGICAL:
        allowed_status = CandidateProposal.Status.MEDICAL_PASSED
        pending_status = CandidateProposal.Status.PSYCHOLOGICAL_PENDING
    else:
        raise ValidationError("Неизвестный вид обследования.")
    if candidate.status != allowed_status:
        raise ValidationError("Нарушен порядок прохождения обследований.")
    screening, created = Screening.objects.get_or_create(candidate=candidate, kind=kind)
    if not created and screening.result != Screening.Result.PENDING:
        raise ValidationError("По обследованию уже вынесено заключение.")
    candidate.status = pending_status
    candidate.save(update_fields=["status", "updated_at"])
    application = candidate.application
    if application.status == JobApplication.Status.APPROVED:
        application.status = JobApplication.Status.SCREENING
        application.save(update_fields=["status", "updated_at"])
    role = User.Role.MEDIC if kind == Screening.Kind.MEDICAL else User.Role.PSYCHOLOGIST
    _notify_enbek(
        application,
        [role],
        "Назначено новое обследование",
        "Жаңа тексеру тағайындалды",
    )
    record_event(actor, "screening.assigned", screening, {"kind": kind})
    _notify_business(
        application, "Кандидат направлен на обследование", "Үміткер тексеруге жіберілді"
    )
    return screening


@transaction.atomic
def review_screening(screening: Screening, result: str, comment: str, document, actor) -> Screening:
    screening = (
        Screening.objects.select_for_update()
        .select_related("candidate__application")
        .get(pk=screening.pk)
    )
    expected_role = User.Role.MEDIC
    if screening.kind == Screening.Kind.PSYCHOLOGICAL:
        expected_role = User.Role.PSYCHOLOGIST
    if actor.role != expected_role:
        raise ValidationError("У вашей роли нет права выносить это заключение.")
    if screening.result != Screening.Result.PENDING:
        raise ValidationError("Заключение уже вынесено.")
    if result not in {Screening.Result.APPROVED, Screening.Result.REJECTED}:
        raise ValidationError("Некорректный результат обследования.")
    comment = comment.strip()
    if not comment:
        raise ValidationError("Укажите комментарий к заключению.")
    if not document:
        raise ValidationError("Прикрепите заключение в формате PDF.")
    if not document.name.lower().endswith(".pdf"):
        raise ValidationError("Заключение должно быть загружено в формате PDF.")
    if document.size > 10 * 1024 * 1024:
        raise ValidationError("Размер заключения не должен превышать 10 МБ.")
    position = document.tell()
    if document.read(5) != b"%PDF-":
        raise ValidationError("Загруженный файл не является PDF-документом.")
    document.seek(position)
    try:
        reader = PdfReader(document, strict=True)
        if reader.is_encrypted:
            raise ValidationError("Загрузите PDF без пароля и шифрования.")
        if not reader.pages:
            raise ValidationError("PDF-заключение не содержит страниц.")
    except (PdfReadError, ValueError, OSError) as exc:
        raise ValidationError("Файл заключения не является корректным PDF.") from exc
    document.seek(position)
    screening.result = result
    screening.comment = comment
    screening.conclusion_document = document
    screening.reviewer = actor
    screening.reviewed_at = timezone.now()
    screening.save(
        update_fields=[
            "result",
            "comment",
            "conclusion_document",
            "reviewer",
            "reviewed_at",
            "updated_at",
        ]
    )
    candidate = screening.candidate
    if screening.kind == Screening.Kind.MEDICAL:
        candidate.status = (
            CandidateProposal.Status.MEDICAL_PASSED
            if result == Screening.Result.APPROVED
            else CandidateProposal.Status.MEDICAL_FAILED
        )
    else:
        candidate.status = (
            CandidateProposal.Status.READY_FOR_CONTRACT
            if result == Screening.Result.APPROVED
            else CandidateProposal.Status.PSYCHOLOGICAL_FAILED
        )
    candidate.save(update_fields=["status", "updated_at"])
    record_event(
        actor,
        "screening.reviewed",
        screening,
        {"result": result, "document": screening.conclusion_document.name},
    )
    _notify_enbek(
        candidate.application,
        [User.Role.ENBEK_EXECUTOR],
        "Получено заключение по обследованию",
        "Тексеру қорытындысы алынды",
    )
    _notify_business(
        candidate.application,
        "Обновлён статус обследования кандидата",
        "Үміткердің тексеру мәртебесі жаңартылды",
    )
    return screening
