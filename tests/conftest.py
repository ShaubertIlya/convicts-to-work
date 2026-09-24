import pytest

from apps.accounts.models import User
from apps.organizations.models import Organization


@pytest.fixture
def enbek():
    return Organization.objects.create(
        name="Тестовое РГП Еңбек",
        kind=Organization.Kind.ENBEK,
        bin="000000000001",
        activity_type="Тестовая деятельность",
        staff_count=10,
        legal_address="Тестовый адрес",
        actual_address="Тестовый адрес",
        actual_address_same=True,
        oked_code="00000",
        bank_details="Тестовые реквизиты",
        director_full_name="Тестовый Руководитель",
        director_iin="000000000001",
        director_position="Руководитель",
        director_email="director@example.test",
        director_phone="+70000000001",
    )


@pytest.fixture
def business():
    return Organization.objects.create(
        name="Тестовое ТОО",
        kind=Organization.Kind.BUSINESS,
        bin="000000000002",
        activity_type="Строительство",
        staff_count=5,
        legal_address="Тестовый адрес 2",
        actual_address="Тестовый адрес 2",
        actual_address_same=True,
        oked_code="41000",
        bank_details="Тестовые реквизиты",
        director_full_name="Тестовый Директор",
        director_iin="000000000002",
        director_position="Директор",
        director_email="business@example.test",
        director_phone="+70000000002",
    )


@pytest.fixture
def make_user():
    def factory(role, organization, email=None):
        email = email or f"{role.lower()}@example.test"
        return User.objects.create_user(
            email=email,
            password="Test-password-123",
            full_name=f"Тестовый {role}",
            role=role,
            organization=organization,
        )

    return factory
