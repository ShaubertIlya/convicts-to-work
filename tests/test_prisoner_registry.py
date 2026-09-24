from datetime import date
from io import BytesIO

import pytest
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.prisoners.models import Prisoner, PrisonerChangeHistory, PrisonerSkill, Skill


@pytest.mark.django_db
def test_enbek_can_filter_and_open_complete_prisoner_case(enbek, make_user):
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    skill = Skill.objects.create(name_ru="Электрик", name_kk="Электрик")
    prisoner = Prisoner.objects.create(
        full_name="Тестовый Специалист",
        iin="900101000099",
        birth_date=date(1990, 1, 1),
        rating=5,
        education="Техническое и профессиональное",
        qualification="Электромонтёр 4 разряда",
        pre_prison_experience="Обслуживание электрооборудования",
        pre_prison_experience_years=7,
        health_status="Практически здоров",
        medical_restrictions="Без ночных смен",
        current_employment="Ремонтная мастерская",
        total_work_experience_years=10,
    )
    PrisonerSkill.objects.create(prisoner=prisoner, skill=skill)
    PrisonerChangeHistory.objects.create(
        prisoner=prisoner,
        change_type=PrisonerChangeHistory.ChangeType.QUALIFICATION,
        effective_date=date(2026, 1, 10),
        previous_value="3 разряд",
        new_value="4 разряд",
    )
    client = APIClient()
    client.force_authenticate(executor)

    response = client.get(
        "/api/prisoners/",
        {"skill": skill.id, "rating": 5, "experience_min": 5, "has_medical_restrictions": "true"},
    )
    details = client.get(f"/api/prisoners/{prisoner.id}/")

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert details.status_code == 200
    assert details.data["qualification"] == "Электромонтёр 4 разряда"
    assert details.data["change_history"][0]["new_value"] == "4 разряд"


@pytest.mark.django_db
def test_business_cannot_access_prisoner_personal_cases(business, make_user):
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business)
    client = APIClient()
    client.force_authenticate(business_admin)

    response = client.get("/api/prisoners/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_prisoner_registry_paginates_and_searches_skills(enbek, make_user):
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    skill = Skill.objects.create(name_ru="Повар", name_kk="Аспаз")
    for index in range(11):
        prisoner = Prisoner.objects.create(
            full_name=f"Кандидат {index}",
            iin=f"900101{index:06d}",
            birth_date=date(1990, 1, 1),
            rating=5 if index == 0 else 2,
        )
        if index == 0:
            PrisonerSkill.objects.create(prisoner=prisoner, skill=skill)
    client = APIClient()
    client.force_authenticate(executor)

    first_page = client.get("/api/prisoners/")
    second_page = client.get("/api/prisoners/", {"page": 2})
    skill_search = client.get("/api/prisoners/", {"search": "Повар", "rating_min": 4})

    assert first_page.data["count"] == 11
    assert len(first_page.data["results"]) == 10
    assert len(second_page.data["results"]) == 1
    assert skill_search.data["count"] == 1


def reference_photo(name="face.jpg", color="blue"):
    content = BytesIO()
    Image.new("RGB", (80, 100), color).save(content, format="JPEG")
    return SimpleUploadedFile(name, content.getvalue(), content_type="image/jpeg")


@pytest.mark.django_db
def test_enbek_can_create_and_edit_prisoner_with_reference_photo_and_history(
    enbek, make_user, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        Prisoner._meta.get_field("photo"),
        "storage",
        FileSystemStorage(location=tmp_path, base_url="/media/"),
    )
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    skill = Skill.objects.create(name_ru="Монтажник", name_kk="Монтажшы")
    client = APIClient()
    client.force_authenticate(executor)

    created = client.post(
        "/api/prisoners/",
        {
            "full_name": "Новый Кандидат",
            "iin": "900101000123",
            "birth_date": "1990-01-01",
            "rating": "3",
            "work_capacity": "CAPABLE",
            "disability_status": "NONE",
            "pension_status": "NONE",
            "pre_prison_experience_years": "0",
            "total_work_experience_years": "0",
            "sentence_start": "",
            "sentence_end": "",
            "qualification": "Монтажник",
            "skill_ids": f'["{skill.id}"]',
            "photo": reference_photo(),
        },
        format="multipart",
    )
    assert created.status_code == 201, created.data
    prisoner = Prisoner.objects.get(pk=created.data["id"])
    assert list(prisoner.skills.values_list("id", flat=True)) == [skill.id]
    assert prisoner.photo.name.startswith("prisoners/reference/")
    assert (tmp_path / prisoner.photo.name).exists()
    old_photo = prisoner.photo.name

    updated = client.patch(
        f"/api/prisoners/{prisoner.id}/",
        {
            "qualification": "Старший монтажник",
            "health_status": "Без ограничений",
            "current_employment": "Мастерская",
            "skill_ids": "[]",
            "photo": reference_photo("replacement.jpg", "green"),
        },
        format="multipart",
    )
    assert updated.status_code == 200, updated.data
    prisoner.refresh_from_db()
    assert prisoner.qualification == "Старший монтажник"
    assert prisoner.skills.count() == 0
    assert prisoner.photo.name != old_photo
    assert (tmp_path / prisoner.photo.name).exists()
    assert (tmp_path / old_photo).exists()
    assert set(prisoner.change_history.values_list("change_type", flat=True)) == {
        PrisonerChangeHistory.ChangeType.QUALIFICATION,
        PrisonerChangeHistory.ChangeType.HEALTH,
        PrisonerChangeHistory.ChangeType.EMPLOYMENT,
    }
    assert client.delete(f"/api/prisoners/{prisoner.id}/").status_code == 405


@pytest.mark.django_db
def test_prisoner_write_validation_and_role(enbek, business, make_user):
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business)
    payload = {
        "full_name": "Проверка",
        "iin": "letters",
        "birth_date": "1990-01-01",
        "rating": 3,
    }
    client = APIClient()
    client.force_authenticate(executor)
    assert client.post("/api/prisoners/", payload).status_code == 400
    payload["iin"] = "900101000124"
    payload["sentence_start"] = "2027-01-01"
    payload["sentence_end"] = "2026-01-01"
    assert client.post("/api/prisoners/", payload).status_code == 400
    payload.pop("sentence_end")
    payload["skill_ids"] = '["not-a-uuid"]'
    assert client.post("/api/prisoners/", payload).status_code == 400
    payload.pop("skill_ids")
    payload["photo"] = SimpleUploadedFile("not-image.jpg", b"invalid", content_type="image/jpeg")
    assert client.post("/api/prisoners/", payload, format="multipart").status_code == 400
    client.force_authenticate(business_admin)
    assert client.post("/api/prisoners/", payload).status_code == 403
