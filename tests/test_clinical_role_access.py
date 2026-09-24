from datetime import date
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfWriter
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications.models import CandidateProposal, JobApplication, Screening
from apps.notifications.models import Notification
from apps.prisoners.models import Prisoner, Skill


def conclusion_file():
    content = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.write(content)
    return SimpleUploadedFile(
        "conclusion.pdf", content.getvalue(), content_type="application/pdf"
    )


@pytest.fixture
def clinical_access_setup(business, enbek, make_user):
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business)
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    medic = make_user(User.Role.MEDIC, enbek)
    psychologist = make_user(User.Role.PSYCHOLOGIST, enbek)
    for recipient in (medic, psychologist):
        Notification.objects.create(
            recipient=recipient,
            title_ru="Назначено обследование",
            title_kk="Тексеру тағайындалды",
        )
    skill = Skill.objects.create(name_ru="Швея", name_kk="Тігінші")

    medical_application = JobApplication.objects.create(
        organization=business,
        created_by=business_admin,
        quantity=1,
        skill=skill,
        skill_requirement=JobApplication.SkillRequirement.REQUIRED,
        workplace_address="Медицинская проверка",
        salary=200000,
        schedule="5/2",
        employment_type=JobApplication.EmploymentType.FULL,
        activity_description="Работы после медицинской проверки",
    )
    psychological_application = JobApplication.objects.create(
        organization=business,
        created_by=business_admin,
        quantity=1,
        skill=skill,
        skill_requirement=JobApplication.SkillRequirement.REQUIRED,
        workplace_address="Психологическая проверка",
        salary=210000,
        schedule="5/2",
        employment_type=JobApplication.EmploymentType.FULL,
        activity_description="Работы после психологической проверки",
    )
    medical_prisoner = Prisoner.objects.create(
        full_name="Кандидат для медика",
        iin="900101000010",
        birth_date=date(1990, 1, 1),
        rating=4,
    )
    psychological_prisoner = Prisoner.objects.create(
        full_name="Кандидат для психолога",
        iin="900101000011",
        birth_date=date(1990, 1, 2),
        rating=5,
    )
    medical_candidate = CandidateProposal.objects.create(
        application=medical_application,
        prisoner=medical_prisoner,
        proposed_by=executor,
    )
    psychological_candidate = CandidateProposal.objects.create(
        application=psychological_application,
        prisoner=psychological_prisoner,
        proposed_by=executor,
    )
    medical_screening = Screening.objects.create(
        candidate=medical_candidate,
        kind=Screening.Kind.MEDICAL,
    )
    psychological_screening = Screening.objects.create(
        candidate=psychological_candidate,
        kind=Screening.Kind.PSYCHOLOGICAL,
    )
    return {
        "medic": medic,
        "psychologist": psychologist,
        "medical_application": medical_application,
        "psychological_application": psychological_application,
        "medical_screening": medical_screening,
        "psychological_screening": psychological_screening,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role_key", "screening_key", "other_screening_key", "application_key"),
    [
        ("medic", "medical_screening", "psychological_screening", "medical_application"),
        (
            "psychologist", "psychological_screening", "medical_screening",
            "psychological_application",
        ),
    ],
)
def test_clinical_roles_work_with_screening_assignments_not_business_applications(
    clinical_access_setup,
    role_key,
    screening_key,
    other_screening_key,
    application_key,
):
    client = APIClient()
    client.force_authenticate(clinical_access_setup[role_key])

    response = client.get("/api/applications/")

    assert response.status_code == 200
    assert response.data["count"] == 0
    assert client.get(
        f"/api/applications/{clinical_access_setup[application_key].id}/"
    ).status_code == 404

    assignments = client.get("/api/applications/screenings/")
    assert assignments.status_code == 200
    assert assignments.data["count"] == 1
    assert assignments.data["results"][0]["id"] == str(
        clinical_access_setup[screening_key].id
    )
    assert client.get(
        f"/api/applications/screenings/{clinical_access_setup[screening_key].id}/"
    ).status_code == 200
    assert client.get(
        f"/api/applications/screenings/{clinical_access_setup[other_screening_key].id}/"
    ).status_code == 404
    assert client.get(
        "/api/applications/screenings/", {"search": "Кандидат для"}
    ).data["count"] == 1
    assert client.get(
        "/api/applications/screenings/", {"result": Screening.Result.APPROVED}
    ).data["count"] == 0


@pytest.mark.django_db
@pytest.mark.parametrize("role_key", ["medic", "psychologist"])
def test_clinical_roles_cannot_open_unrelated_sections(clinical_access_setup, role_key):
    client = APIClient()
    client.force_authenticate(clinical_access_setup[role_key])

    assert client.get("/api/contracts/").status_code == 403
    assert client.get("/api/prisoners/").status_code == 403
    assert client.get("/api/organizations/").status_code == 403
    assert client.get("/api/prisoners/skills/").status_code == 200
    assert client.get("/api/notifications/").status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role_key", "screening_key"),
    [
        ("medic", "medical_screening"),
        ("psychologist", "psychological_screening"),
    ],
)
def test_clinical_review_requires_and_stores_pdf_conclusion(
    clinical_access_setup,
    role_key,
    screening_key,
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    client = APIClient()
    client.force_authenticate(clinical_access_setup[role_key])
    screening = clinical_access_setup[screening_key]
    endpoint = f"/api/applications/screenings/{screening.id}/review/"

    response = client.post(
        endpoint,
        {"result": Screening.Result.APPROVED, "comment": "Допущен к работе"},
        format="multipart",
    )
    assert response.status_code == 400

    broken_pdf = client.post(
        endpoint,
        {
            "result": Screening.Result.APPROVED,
            "comment": "Допущен к работе",
            "document": SimpleUploadedFile(
                "broken.pdf", b"%PDF-1.4\ncorrupt", content_type="application/pdf"
            ),
        },
        format="multipart",
    )
    assert broken_pdf.status_code == 400

    response = client.post(
        endpoint,
        {
            "result": Screening.Result.APPROVED,
            "comment": "Допущен к работе",
            "document": conclusion_file(),
        },
        format="multipart",
    )

    assert response.status_code == 200
    assert response.data["conclusion_document"].endswith(".pdf")
    screening.refresh_from_db()
    assert screening.result == Screening.Result.APPROVED
    assert screening.comment == "Допущен к работе"
    assert screening.conclusion_document.name.endswith(".pdf")
