from datetime import date
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfWriter
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications import services
from apps.applications.models import CandidateProposal, JobApplication, Screening
from apps.organizations.models import Bank
from apps.prisoners.models import Prisoner, PrisonerSkill, Skill


def conclusion_file(name="conclusion.pdf"):
    content = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.write(content)
    return SimpleUploadedFile(
        name,
        content.getvalue(),
        content_type="application/pdf",
    )


@pytest.fixture
def application_setup(business, enbek, make_user):
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business)
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    manager = make_user(User.Role.ENBEK_MANAGER, enbek)
    medic = make_user(User.Role.MEDIC, enbek)
    psychologist = make_user(User.Role.PSYCHOLOGIST, enbek)
    skill = Skill.objects.create(name_ru="Сварщик", name_kk="Дәнекерлеуші")
    application = JobApplication.objects.create(
        organization=business,
        created_by=business_admin,
        quantity=1,
        skill=skill,
        skill_requirement=JobApplication.SkillRequirement.REQUIRED,
        workplace_address="Тестовый объект",
        salary=200000,
        schedule="5/2",
        employment_type=JobApplication.EmploymentType.FULL,
        activity_description="Тестовые работы",
    )
    skilled = Prisoner.objects.create(
        full_name="Тестовый Кандидат 1",
        iin="900101000001",
        birth_date=date(1990, 1, 1),
        rating=5,
    )
    unskilled = Prisoner.objects.create(
        full_name="Тестовый Кандидат 2",
        iin="900101000002",
        birth_date=date(1990, 1, 2),
        rating=4,
    )
    PrisonerSkill.objects.create(prisoner=skilled, skill=skill)
    return {
        "application": application,
        "executor": executor,
        "manager": manager,
        "medic": medic,
        "psychologist": psychologist,
        "skilled": skilled,
        "unskilled": unskilled,
    }


@pytest.mark.django_db
def test_required_skill_and_quantity_are_enforced(application_setup):
    data = application_setup
    application = services.submit_application(data["application"])
    with pytest.raises(ValidationError):
        services.propose_candidates(application, "not-a-list", data["executor"])
    with pytest.raises(ValidationError):
        services.propose_candidates(application, [data["unskilled"].id], data["executor"])
    with pytest.raises(ValidationError):
        services.propose_candidates(
            application,
            [data["skilled"].id, data["unskilled"].id],
            data["executor"],
        )


@pytest.mark.django_db
def test_submitted_application_keeps_current_structured_company_requisites(
    application_setup, business
):
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

    application = services.submit_application(application_setup["application"])

    assert application.organization_snapshot["oked"]["code"] == business.oked_code
    assert application.organization_snapshot["bank"]["bik"] == bank.bic
    assert application.organization_snapshot["kbe"] == "17"
    assert application.organization_snapshot["iik"] == "KZ168562203138317128"


@pytest.mark.django_db
def test_only_business_organization_can_edit_application_and_only_while_draft(
    application_setup,
):
    application = application_setup["application"]
    owner = application.created_by
    client = APIClient()

    client.force_authenticate(owner)
    response = client.patch(
        f"/api/applications/{application.id}/",
        {"schedule": "2/2, 08:00–20:00"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["schedule"] == "2/2, 08:00–20:00"

    client.force_authenticate(application_setup["executor"])
    response = client.patch(
        f"/api/applications/{application.id}/",
        {"schedule": "Запрещённое изменение"},
        format="json",
    )
    assert response.status_code == 400

    services.submit_application(application)
    client.force_authenticate(owner)
    response = client.patch(
        f"/api/applications/{application.id}/",
        {"schedule": "После отправки"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_screenings_must_be_medical_then_psychological(
    application_setup, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    data = application_setup
    application = services.submit_application(data["application"])
    services.propose_candidates(application, [data["skilled"].id], data["executor"])
    proposal = CandidateProposal.objects.get(application=application)
    services.business_respond(application, [proposal.id])
    services.enbek_decide(application, True)
    proposal.refresh_from_db()

    with pytest.raises(ValidationError):
        services.send_to_screening(proposal, Screening.Kind.PSYCHOLOGICAL)

    medical = services.send_to_screening(proposal, Screening.Kind.MEDICAL)
    services.review_screening(
        medical,
        Screening.Result.APPROVED,
        "Допущен",
        conclusion_file("medical.pdf"),
        data["medic"],
    )
    proposal.refresh_from_db()
    psychological = services.send_to_screening(proposal, Screening.Kind.PSYCHOLOGICAL)
    services.review_screening(
        psychological,
        Screening.Result.APPROVED,
        "Допущен",
        conclusion_file("psychological.pdf"),
        data["psychologist"],
    )
    proposal.refresh_from_db()
    assert proposal.status == CandidateProposal.Status.READY_FOR_CONTRACT


@pytest.mark.django_db
def test_enbek_manager_can_start_screening_for_business_accepted_candidate(application_setup):
    data = application_setup
    application = services.submit_application(data["application"])
    services.propose_candidates(application, [data["skilled"].id], data["executor"])
    proposal = CandidateProposal.objects.get(application=application)
    services.business_respond(application, [proposal.id])
    services.enbek_decide(application, True)

    client = APIClient()
    client.force_authenticate(data["manager"])
    invalid = client.post(
        f"/api/applications/{application.id}/send-to-screening/",
        {"candidate_id": "not-a-uuid", "kind": Screening.Kind.MEDICAL},
        format="json",
    )
    assert invalid.status_code == 400
    response = client.post(
        f"/api/applications/{application.id}/send-to-screening/",
        {"candidate_id": str(proposal.id), "kind": Screening.Kind.MEDICAL},
        format="json",
    )

    assert response.status_code == 201
    proposal.refresh_from_db()
    assert proposal.status == CandidateProposal.Status.MEDICAL_PENDING


@pytest.mark.django_db
def test_business_sees_screening_progress_without_medical_details(
    application_setup, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    data = application_setup
    application = services.submit_application(data["application"])
    services.propose_candidates(application, [data["skilled"].id], data["executor"])
    proposal = CandidateProposal.objects.get(application=application)
    services.business_respond(application, [proposal.id])
    services.enbek_decide(application, True)
    screening = services.send_to_screening(proposal, Screening.Kind.MEDICAL)
    services.review_screening(
        screening, Screening.Result.APPROVED, "Конфиденциальное заключение",
        conclusion_file(), data["medic"],
    )

    client = APIClient()
    client.force_authenticate(application.created_by)
    response = client.get(f"/api/applications/{application.id}/")
    assert response.status_code == 200
    visible_screening = response.data["candidates"][0]["screenings"][0]
    assert visible_screening["result"] == Screening.Result.APPROVED
    for private_field in (
        "prisoner_name", "comment", "conclusion_document",
        "conclusion_file_name", "reviewer_name",
    ):
        assert private_field not in visible_screening

    response = client.get("/api/applications/screenings/")
    assert response.status_code == 200
    for private_field in (
        "prisoner_name", "comment", "conclusion_document",
        "conclusion_file_name", "reviewer_name",
    ):
        assert private_field not in response.data["results"][0]

    CandidateProposal.objects.create(
        application=application, prisoner=data["unskilled"],
        proposed_by=data["executor"], status=CandidateProposal.Status.ENBEK_APPROVED,
    )
    client.force_authenticate(data["medic"])
    medical_view = client.get(f"/api/applications/{application.id}/")
    assert medical_view.status_code == 404
    medical_assignment = client.get(f"/api/applications/screenings/{screening.id}/")
    assert medical_assignment.status_code == 200
    assert medical_assignment.data["prisoner_name"] == data["skilled"].full_name
    assert medical_assignment.data["comment"] == "Конфиденциальное заключение"


@pytest.mark.django_db
def test_application_registry_filters_and_paginates(application_setup):
    original = application_setup["application"]
    for index in range(10):
        JobApplication.objects.create(
            organization=original.organization,
            created_by=original.created_by,
            quantity=1,
            skill=original.skill,
            skill_requirement=original.skill_requirement,
            workplace_address=f"Объект {index}",
            salary=original.salary,
            schedule=original.schedule,
            employment_type=original.employment_type,
            activity_description=original.activity_description,
            status=JobApplication.Status.SUBMITTED,
        )
    client = APIClient()
    client.force_authenticate(application_setup["executor"])

    first_page = client.get("/api/applications/")
    second_page = client.get("/api/applications/", {"page": 2})
    submitted = client.get("/api/applications/", {"status": JobApplication.Status.SUBMITTED})

    assert first_page.status_code == 200
    assert first_page.data["count"] == 11
    assert len(first_page.data["results"]) == 10
    assert len(second_page.data["results"]) == 1
    assert submitted.data["count"] == 10
