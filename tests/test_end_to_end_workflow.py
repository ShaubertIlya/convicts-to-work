from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from pypdf import PdfWriter
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications.models import CandidateProposal, JobApplication, Screening
from apps.contracts.models import ContractSignature, EmploymentContract
from apps.organizations.models import Bank, OkedCode
from apps.prisoners.models import Prisoner, Skill


def image_file(name, image_format, color):
    output = BytesIO()
    Image.new("RGB", (100, 120), color).save(output, format=image_format)
    return SimpleUploadedFile(
        name, output.getvalue(),
        content_type="image/png" if image_format == "PNG" else "image/jpeg",
    )


def pdf_file(name):
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.write(output)
    return SimpleUploadedFile(name, output.getvalue(), content_type="application/pdf")


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_registered_business_to_signed_contract_uses_latest_uploaded_reference_photo(
    enbek, make_user, settings, tmp_path, monkeypatch
):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.setattr(
        Prisoner._meta.get_field("photo"), "storage",
        FileSystemStorage(location=tmp_path, base_url="/media/"),
    )
    bank = Bank.objects.create(
        bic="KCJBKZKX", bank_code="856",
        name_ru="АО «Банк ЦентрКредит»", name_kk="«Банк ЦентрКредит» АҚ",
    )
    OkedCode.objects.create(
        code="41201", name_ru="Строительство жилых зданий",
        name_kk="Тұрғын үй құрылысы",
    )
    business = APIClient()
    registered = business.post("/api/auth/register/", {
        "email": "workflow@example.test", "password": "Secure-password-123",
        "full_name": "Администратор МСБ", "name": "Тестовое ТОО",
        "bin": "123456789012", "activity_type": "Строительство", "staff_count": 12,
        "legal_address": "г. Тест, ул. Тестовая, 1", "actual_address_same": True,
        "oked_code": "41201", "bank": str(bank.id), "kbe": "17",
        "iik": "KZ168562203138317128", "director_full_name": "Тестовый Директор",
        "director_iin": "000000000003", "director_position": "Директор",
        "director_email": "director@example.test", "director_phone": "+77000000003",
    }, format="json")
    assert registered.status_code == 201, registered.data
    assert "auth_token" not in registered.cookies
    logged_in = business.post("/api/auth/login/", {
        "email": "workflow@example.test", "password": "Secure-password-123",
    }, format="json")
    assert logged_in.status_code == 200, logged_in.data
    assert "auth_token" in logged_in.cookies
    assert business.get("/api/auth/me/").status_code == 200

    executor = client_for(make_user(User.Role.ENBEK_EXECUTOR, enbek))
    manager = client_for(make_user(User.Role.ENBEK_MANAGER, enbek))
    medic = client_for(make_user(User.Role.MEDIC, enbek))
    psychologist = client_for(make_user(User.Role.PSYCHOLOGIST, enbek))
    skill = Skill.objects.create(name_ru="Сварщик", name_kk="Дәнекерлеуші")

    created_prisoner = executor.post("/api/prisoners/", {
        "full_name": "Тестовый Кандидат", "iin": "900101000155",
        "birth_date": "1990-01-01", "rating": "4",
        "skill_ids": f'["{skill.id}"]',
        "photo": image_file("first.jpg", "JPEG", "blue"),
    }, format="multipart")
    assert created_prisoner.status_code == 201, created_prisoner.data
    prisoner_id = created_prisoner.data["id"]
    old_photo = created_prisoner.data["photo"]
    latest_photo = image_file("current.png", "PNG", "green")
    latest_bytes = latest_photo.read()
    latest_photo.seek(0)
    edited_prisoner = executor.patch(f"/api/prisoners/{prisoner_id}/", {
        "photo": latest_photo, "qualification": "Сварщик 4 разряда",
    }, format="multipart")
    assert edited_prisoner.status_code == 200, edited_prisoner.data
    assert edited_prisoner.data["photo"] != old_photo
    assert edited_prisoner.data["photo"].endswith(".png")
    assert Prisoner.objects.get(pk=prisoner_id).photo.read() == latest_bytes

    application = business.post("/api/applications/", {
        "quantity": 1, "skill": str(skill.id), "skill_requirement": "REQUIRED",
        "workplace_address": "Тестовая площадка", "salary": "200000.00",
        "schedule": "5/2", "employment_type": "FULL",
        "activity_description": "Тестовые сварочные работы",
    }, format="json")
    assert application.status_code == 201, application.data
    application_id = application.data["id"]
    assert application.data["status"] == JobApplication.Status.DRAFT
    submitted = business.post(f"/api/applications/{application_id}/submit/")
    assert submitted.status_code == 200, submitted.data
    assert submitted.data["organization_snapshot"]["bank"]["bik"] == bank.bic
    proposed = executor.post(f"/api/applications/{application_id}/propose/", {
        "prisoner_ids": [prisoner_id],
    }, format="json")
    assert proposed.status_code == 200, proposed.data
    candidate_id = proposed.data["candidates"][0]["id"]
    selected = business.post(f"/api/applications/{application_id}/business-response/", {
        "accepted_candidate_ids": [candidate_id],
    }, format="json")
    assert selected.status_code == 200, selected.data
    approved = manager.post(f"/api/applications/{application_id}/enbek-decision/", {
        "approved": True,
    }, format="json")
    assert approved.status_code == 200, approved.data

    for kind, reviewer in (("MEDICAL", medic), ("PSYCHOLOGICAL", psychologist)):
        assignment = executor.post(f"/api/applications/{application_id}/send-to-screening/", {
            "candidate_id": candidate_id, "kind": kind,
        }, format="json")
        assert assignment.status_code == 201, assignment.data
        screening_id = assignment.data["id"]
        visible = reviewer.get("/api/applications/screenings/")
        assert visible.status_code == 200
        assert screening_id in {row["id"] for row in visible.data["results"]}
        reviewed = reviewer.post(f"/api/applications/screenings/{screening_id}/review/", {
            "result": "APPROVED", "comment": "Допущен к работе",
            "document": pdf_file(f"{kind.lower()}.pdf"),
        }, format="multipart")
        assert reviewed.status_code == 200, reviewed.data
        assert reviewed.data["result"] == Screening.Result.APPROVED

    assert (
        CandidateProposal.objects.get(pk=candidate_id).status
        == CandidateProposal.Status.READY_FOR_CONTRACT
    )
    created_contract = executor.post("/api/contracts/create-from-application/", {
        "application_id": application_id, "candidate_ids": [candidate_id],
        "starts_on": "2026-09-23", "ends_on": "2027-09-23",
    }, format="json")
    assert created_contract.status_code == 201, created_contract.data
    contract_id = created_contract.data[0]["id"]
    uploaded = executor.post(f"/api/contracts/{contract_id}/upload-document/", {
        "document": pdf_file("contract.pdf"),
    }, format="multipart")
    assert uploaded.status_code == 200, uploaded.data

    state = {}

    def biometric_request(url, **kwargs):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                if url.endswith("/start"):
                    return {"verification_id": "verification-workflow", "expires_in": 120}
                return {"verified": True, "status": "CONSUMED"}

        if url.endswith("/start"):
            state["value"] = kwargs["data"]["state"]
            filename, uploaded_file, content_type = kwargs["files"]["reference_image"]
            assert filename.endswith("current.png")
            assert content_type == "image/png"
            assert uploaded_file.read() == latest_bytes
        else:
            assert url.endswith("/verification-workflow/consume")
        return Response()

    with patch("apps.contracts.biometry.httpx.post", side_effect=biometric_request):
        started = executor.post(f"/api/contracts/{contract_id}/start-prisoner-signature/", {
            "acknowledged": True,
        }, format="json")
        assert started.status_code == 201, started.data
        assert started.data["redirect_url"].endswith(
            "/biometry/?verification_id=verification-workflow"
        )
        callback = APIClient().get("/api/contracts/biometry/callback/", {
            "verification_id": "verification-workflow",
            "state": state["value"], "outcome": "success",
        })
    assert callback.status_code == 302
    assert "biometry=success" in callback.url
    assert ContractSignature.objects.filter(contract_id=contract_id, party="PRISONER").exists()

    business_signed = business.post(f"/api/contracts/{contract_id}/sign/")
    assert business_signed.status_code == 200, business_signed.data
    manager_signed = manager.post(f"/api/contracts/{contract_id}/sign/")
    assert manager_signed.status_code == 200, manager_signed.data
    assert EmploymentContract.objects.get(pk=contract_id).status == EmploymentContract.Status.ACTIVE
    assert JobApplication.objects.get(pk=application_id).status == JobApplication.Status.COMPLETED
    assert ContractSignature.objects.filter(contract_id=contract_id).count() == 3
