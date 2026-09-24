from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.prisoners.models import Prisoner, PrisonerSkill, Skill


@pytest.mark.django_db
def test_public_stats_expose_counts_but_no_personal_data():
    skill = Skill.objects.create(name_ru="Электрик", name_kk="Электрик")
    prisoner = Prisoner.objects.create(
        full_name="Скрытое Имя",
        iin="900101000020",
        birth_date=date(1990, 1, 1),
        rating=5,
    )
    PrisonerSkill.objects.create(prisoner=prisoner, skill=skill)

    response = APIClient().get("/api/public/stats/")

    assert response.status_code == 200
    assert response.json()["total_available"] == 1
    assert response.json()["by_skill"][0]["count"] == 1
    assert "Скрытое Имя" not in response.content.decode()
    assert "900101000020" not in response.content.decode()
