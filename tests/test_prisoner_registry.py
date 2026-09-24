from datetime import date

import pytest
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
