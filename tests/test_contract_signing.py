from datetime import date, timedelta
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from pypdf import PdfWriter
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications.models import CandidateProposal, JobApplication
from apps.contracts import services
from apps.contracts.models import BiometricSignatureAttempt, ContractSignature, EmploymentContract
from apps.organizations.models import Bank
from apps.organizations.snapshots import build_organization_snapshot
from apps.prisoners.models import Prisoner, Skill


class FakeBiometryClient:
    def start(self, reference_file, state):
        assert reference_file.read()
        assert len(state) >= 16
        return {"verification_id": "verification-test-1", "expires_in": 120}

    def consume(self, verification_id):
        assert verification_id == "verification-test-1"
        return {"verified": True, "status": "CONSUMED"}

    def frontend_url(self, verification_id):
        return f"http://biometry.test/biometry/?verification_id={verification_id}"


def photo_file():
    content = BytesIO()
    Image.new("RGB", (40, 40), "#315b4a").save(content, format="JPEG")
    return SimpleUploadedFile("reference.jpg", content.getvalue(), content_type="image/jpeg")


def contract_pdf():
    content = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.write(content)
    return SimpleUploadedFile("contract.pdf", content.getvalue(), content_type="application/pdf")


@pytest.mark.django_db
def test_create_contracts_endpoint_with_optional_bank_join(business, enbek, make_user):
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business)
    skill = Skill.objects.create(name_ru="Сварщик", name_kk="Дәнекерлеуші")
    application = JobApplication.objects.create(
        organization=business,
        created_by=business_admin,
        quantity=3,
        skill=skill,
        skill_requirement=JobApplication.SkillRequirement.REQUIRED,
        workplace_address="Тестовая строительная площадка",
        salary=200000,
        schedule="5/2, 09:00–18:00",
        employment_type=JobApplication.EmploymentType.FULL,
        activity_description="Тестовые сварочные работы на площадке",
        status=JobApplication.Status.SCREENING,
    )
    candidate_ids = []
    for index in range(3):
        prisoner = Prisoner.objects.create(
            full_name=f"Тестовый кандидат {index + 1}",
            iin=f"900101{index + 1:06d}",
            birth_date=date(1990, 1, index + 1),
            rating=3,
        )
        candidate = CandidateProposal.objects.create(
            application=application,
            prisoner=prisoner,
            proposed_by=executor,
            status=CandidateProposal.Status.READY_FOR_CONTRACT,
        )
        candidate_ids.append(str(candidate.id))

    client = APIClient()
    client.force_authenticate(executor)
    response = client.post(
        "/api/contracts/create-from-application/",
        {
            "application_id": str(application.id),
            "candidate_ids": candidate_ids,
            "starts_on": "2026-09-23",
            "ends_on": "2027-09-23",
        },
        format="json",
    )

    assert response.status_code == 201
    assert len(response.data) == 3
    assert EmploymentContract.objects.filter(application=application).count() == 3
    application.refresh_from_db()
    assert application.status == JobApplication.Status.CONTRACTING


@pytest.mark.django_db
def test_prisoner_must_sign_first_and_all_parties_activate_contract(
    business, enbek, make_user, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business)
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    manager = make_user(User.Role.ENBEK_MANAGER, enbek)
    bank = Bank.objects.create(
        bic="KCJBKZKX",
        bank_code="856",
        name_ru="АО «Банк ЦентрКредит»",
        name_kk="«Банк ЦентрКредит» АҚ",
    )
    business.bank = bank
    business.kbe = "17"
    business.iik = "KZ168562203138317128"
    business.save(update_fields=["bank", "kbe", "iik", "updated_at"])
    skill = Skill.objects.create(name_ru="Плотник", name_kk="Ағаш ұстасы")
    prisoner = Prisoner.objects.create(
        full_name="Тестовый Кандидат",
        iin="900101000010",
        birth_date=date(1990, 1, 1),
        rating=3,
        photo=photo_file(),
    )
    application = JobApplication.objects.create(
        organization=business,
        created_by=business_admin,
        quantity=2,
        skill=skill,
        skill_requirement=JobApplication.SkillRequirement.TRAINING_ALLOWED,
        workplace_address="Тестовый объект",
        salary=200000,
        schedule="5/2",
        employment_type=JobApplication.EmploymentType.FULL,
        activity_description="Тестовые работы",
        status=JobApplication.Status.SCREENING,
    )
    proposal = CandidateProposal.objects.create(
        application=application,
        prisoner=prisoner,
        proposed_by=executor,
        status=CandidateProposal.Status.READY_FOR_CONTRACT,
    )
    another_prisoner = Prisoner.objects.create(
        full_name="Тестовый Кандидат 2", iin="900101000011",
        birth_date=date(1990, 1, 2), rating=2,
    )
    pending_proposal = CandidateProposal.objects.create(
        application=application, prisoner=another_prisoner, proposed_by=executor,
        status=CandidateProposal.Status.MEDICAL_PENDING,
    )
    application.organization_snapshot = build_organization_snapshot(business)
    application.save(update_fields=["organization_snapshot"])
    business.legal_address = "Новый адрес после подачи заявки"
    business.save(update_fields=["legal_address"])
    with pytest.raises(ValidationError):
        services.create_contracts(
            application, [proposal.id, proposal.id],
            date.today(), services._annual_end(date.today()),
        )
    with pytest.raises(ValidationError, match="12 месяцев"):
        services.create_contracts(
            application, [proposal.id], date.today(), date.today() + timedelta(days=30)
        )
    contract = services.create_contracts(
        application,
        [proposal.id],
        date.today(),
        date.today() + timedelta(days=365),
    )[0]
    assert contract.organization_snapshot["oked"]["code"] == business.oked_code
    assert contract.organization_snapshot["bank"]["bik"] == bank.bic
    assert contract.organization_snapshot["kbe"] == "17"
    assert contract.organization_snapshot["iik"] == "KZ168562203138317128"
    assert contract.organization_snapshot["legal_address"] == "Тестовый адрес 2"

    with pytest.raises(ValidationError, match="PDF-документ"):
        services.start_prisoner_signature(contract, executor, acknowledged=True)
    contract = services.upload_contract_document(contract, contract_pdf(), executor)
    assert len(contract.document_hash) == 64
    with pytest.raises(ValidationError, match="ознакомился"):
        services.start_prisoner_signature(contract, executor)

    with pytest.raises(ValidationError):
        services.button_sign(contract, business_admin)

    started = services.start_prisoner_signature(
        contract, executor, acknowledged=True, client=FakeBiometryClient()
    )
    attempt = contract.biometric_attempts.get()
    raw_state = None
    # The application intentionally stores only a digest; this test reconstructs
    # a valid callback by replacing the generated attempt with a known digest.
    raw_state = "known-test-state-123456789"
    attempt.state_digest = services._state_digest(raw_state)
    attempt.save(update_fields=["state_digest"])
    assert started["verification_id"] == "verification-test-1"
    assert services.biometry_contract_number("verification-test-1", raw_state) == contract.number
    assert services.biometry_contract_number("verification-test-1", "wrong-state") is None
    with patch.object(
        FakeBiometryClient, "consume", return_value={"verified": False, "status": "VERIFIED"}
    ):
        with pytest.raises(ValidationError, match="одноразовый результат"):
            services.complete_biometry(
                "verification-test-1", raw_state, "success", client=FakeBiometryClient()
            )
    attempt.refresh_from_db()
    assert attempt.status == BiometricSignatureAttempt.Status.PENDING
    assert not contract.signatures.exists()
    contract = services.complete_biometry(
        "verification-test-1", raw_state, "success", client=FakeBiometryClient()
    )
    assert contract.status == EmploymentContract.Status.PARTIALLY_SIGNED
    assert contract.signatures.get(party=ContractSignature.Party.PRISONER).evidence[
        "consent_acknowledged_at"
    ]
    with patch.object(
        FakeBiometryClient, "consume", side_effect=AssertionError("repeated consume")
    ):
        repeated = services.complete_biometry(
            "verification-test-1", raw_state, "success", client=FakeBiometryClient()
        )
    assert repeated.id == contract.id
    assert contract.signatures.filter(party=ContractSignature.Party.PRISONER).count() == 1

    services.button_sign(contract, business_admin)
    contract = services.button_sign(contract, manager)
    contract.refresh_from_db()
    assert contract.status == EmploymentContract.Status.ACTIVE
    assert set(contract.signatures.values_list("party", flat=True)) == {
        ContractSignature.Party.PRISONER,
        ContractSignature.Party.BUSINESS_ADMIN,
        ContractSignature.Party.ENBEK_MANAGER,
    }
    application.refresh_from_db()
    assert application.status == JobApplication.Status.CONTRACTING

    pending_proposal.status = CandidateProposal.Status.MEDICAL_FAILED
    pending_proposal.save(update_fields=["status"])
    services._refresh_contract_status(contract)
    application.refresh_from_db()
    assert application.status == JobApplication.Status.COMPLETED


@override_settings(FRONTEND_PUBLIC_URL="http://localhost:3000")
def test_biometry_callback_returns_to_contract_registry():
    client = APIClient()
    with patch("apps.contracts.views.services.biometry_contract_number", return_value=None), patch(
        "apps.contracts.views.services.complete_biometry",
        return_value=SimpleNamespace(number="TD-2026-000001"),
    ):
        response = client.get("/api/contracts/biometry/callback/", {"outcome": "success"})
    assert response.status_code == 302
    assert response.url == "http://localhost:3000/contracts?number=TD-2026-000001&biometry=success"

    with patch(
        "apps.contracts.views.services.biometry_contract_number",
        return_value="TD-2026-000001",
    ), patch(
        "apps.contracts.views.services.complete_biometry",
        side_effect=ValidationError("Неверная попытка"),
    ):
        response = client.get("/api/contracts/biometry/callback/", {"outcome": "failed"})
    assert response.status_code == 302
    assert response.url == "http://localhost:3000/contracts?biometry=error&number=TD-2026-000001"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("outcome", "expected_status"),
    [
        ("failed", BiometricSignatureAttempt.Status.FAILED),
        ("expired", BiometricSignatureAttempt.Status.EXPIRED),
    ],
)
def test_unsuccessful_biometry_does_not_sign_contract(
    business, enbek, make_user, settings, tmp_path, outcome, expected_status
):
    settings.MEDIA_ROOT = tmp_path
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business)
    skill = Skill.objects.create(name_ru="Столяр", name_kk="Ағаш шебері")
    prisoner = Prisoner.objects.create(
        full_name="Тестовый Работник", iin="900101000099",
        birth_date=date(1990, 1, 1), rating=3, photo=photo_file(),
    )
    application = JobApplication.objects.create(
        organization=business, created_by=business_admin, quantity=1, skill=skill,
        skill_requirement=JobApplication.SkillRequirement.REQUIRED,
        workplace_address="Тестовый объект", salary=200000, schedule="5/2",
        employment_type=JobApplication.EmploymentType.FULL,
        activity_description="Тестовые столярные работы",
        status=JobApplication.Status.SCREENING,
    )
    proposal = CandidateProposal.objects.create(
        application=application, prisoner=prisoner, proposed_by=executor,
        status=CandidateProposal.Status.READY_FOR_CONTRACT,
    )
    contract = services.create_contracts(
        application, [proposal.id], date(2026, 9, 23), date(2027, 9, 23)
    )[0]
    contract = services.upload_contract_document(contract, contract_pdf(), executor)
    services.start_prisoner_signature(
        contract, executor, acknowledged=True, client=FakeBiometryClient()
    )
    attempt = contract.biometric_attempts.get()
    raw_state = "failed-test-state-123456789"
    attempt.state_digest = services._state_digest(raw_state)
    attempt.save(update_fields=["state_digest"])

    with patch.object(FakeBiometryClient, "consume", side_effect=AssertionError("no consume")):
        with pytest.raises(ValidationError):
            services.complete_biometry(
                attempt.verification_id, raw_state, outcome, client=FakeBiometryClient()
            )

    attempt.refresh_from_db()
    contract.refresh_from_db()
    assert attempt.status == expected_status
    assert contract.status == EmploymentContract.Status.AWAITING_PRISONER
    assert not contract.signatures.exists()
