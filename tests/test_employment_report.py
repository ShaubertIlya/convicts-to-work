from datetime import date, datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.applications.models import CandidateProposal, JobApplication
from apps.contracts.models import ContractSignature, EmploymentContract
from apps.prisoners.models import Prisoner, Skill


@pytest.mark.django_db
def test_leadership_report_counts_distinct_signed_employment_on_date(enbek, business, make_user):
    manager = make_user(User.Role.ENBEK_MANAGER, enbek)
    business_user = make_user(User.Role.BUSINESS_ADMIN, business)
    skill = Skill.objects.create(name_ru="Столяр", name_kk="Ағаш ұстасы")
    prisoners = []
    for index, capacity in enumerate(["CAPABLE", "UNABLE", "UNKNOWN"], start=1):
        prisoners.append(Prisoner.objects.create(
            full_name=f"Кандидат {index}",
            iin=f"900101{index:06d}",
            birth_date=date(1990, 1, index),
            rating=3,
            sentence_start=date(2026, 1, 1),
            sentence_end=date(2027, 1, 1),
            work_capacity=capacity,
            education="Среднее" if index < 3 else "Высшее",
            qualification="Столяр" if index < 3 else "Электрик",
            penitentiary_education="Курс столяра" if index == 1 else "",
        ))
    application = JobApplication.objects.create(
        organization=business,
        created_by=business_user,
        quantity=2,
        skill=skill,
        skill_requirement=JobApplication.SkillRequirement.REQUIRED,
        workplace_address="Тестовый адрес",
        salary=100000,
        schedule="5/2",
        employment_type=JobApplication.EmploymentType.FULL,
        activity_description="Тестовая работа",
    )
    for index, prisoner in enumerate(prisoners[:2], start=1):
        candidate = CandidateProposal.objects.create(
            application=application, prisoner=prisoner, proposed_by=manager
        )
        contract = EmploymentContract.objects.create(
            number=f"REPORT-2026-{index}",
            application=application,
            candidate=candidate,
            prisoner=prisoner,
            organization=business,
            starts_on=date(2026, 9, 1),
            ends_on=date(2026, 10, 1),
        )
        for party in ContractSignature.Party.values[:(3 if index == 1 else 2)]:
            ContractSignature.objects.create(
                contract=contract,
                party=party,
                method=ContractSignature.Method.BUTTON,
                signed_by=manager,
                signed_at=timezone.make_aware(datetime(2026, 9, 15, 12)),
            )

    client = APIClient()
    client.force_authenticate(manager)
    before = client.get("/api/reports/employment/", {"as_of": "2026-09-10"})
    current = client.get("/api/reports/employment/", {"as_of": "2026-09-20"})

    assert before.status_code == 200
    assert before.data["employed_total"] == 0
    assert current.status_code == 200
    assert current.data["population_total"] == 3
    assert current.data["employed_total"] == 1
    assert current.data["employment_rate_total"] == 33.3
    assert current.data["work_capable_total"] == 1
    assert current.data["work_capable_employed"] == 1
    assert current.data["employment_rate_capable"] == 100.0
    assert current.data["work_capacity_unknown"] == 1
    assert current.data["education"] == [
        {"label": "Среднее", "count": 2}, {"label": "Высшее", "count": 1}
    ]


@pytest.mark.django_db
def test_leadership_report_rejects_other_roles_and_invalid_dates(enbek, business, make_user):
    manager = make_user(User.Role.ENBEK_MANAGER, enbek)
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek)
    business_user = make_user(User.Role.BUSINESS_ADMIN, business)
    client = APIClient()

    for user in [executor, business_user]:
        client.force_authenticate(user)
        assert client.get("/api/reports/employment/").status_code == 403

    client.force_authenticate(manager)
    assert client.get("/api/reports/employment/", {"as_of": "not-a-date"}).status_code == 400
    empty = client.get("/api/reports/employment/")
    assert empty.status_code == 200
    assert empty.data["employment_rate_total"] is None
    assert empty.data["employment_rate_capable"] is None
