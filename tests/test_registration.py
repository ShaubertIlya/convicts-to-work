import pytest
from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organizations.models import Bank, OkedCode, Organization
from apps.organizations.serializers import OrganizationSerializer


def registration_payload(bank):
    return {
        "email": "admin@example.test",
        "password": "Secure-password-123",
        "full_name": "Тестовый Администратор",
        "name": "Тестовое ТОО",
        "bin": "123456789012",
        "activity_type": "Строительство",
        "staff_count": 12,
        "legal_address": "г. Тест, ул. Тестовая, 1",
        "actual_address": "",
        "actual_address_same": True,
        "oked_code": "41201",
        "bank": str(bank.id),
        "kbe": "17",
        "iik": "KZ168562203138317128",
        "licenses": "",
        "director_full_name": "Тестовый Директор",
        "director_iin": "000000000003",
        "director_position": "Директор",
        "director_email": "director@example.test",
        "director_phone": "+77000000003",
    }


@pytest.fixture
def registration_references(db):
    OkedCode.objects.create(
        code="41201",
        name_ru="Строительство жилых зданий",
        name_kk="Тұрғын үй құрылысы",
    )
    return Bank.objects.create(
        bic="KCJBKZKX",
        bank_code="856",
        name_ru="АО «Банк ЦентрКредит»",
        name_kk="«Банк ЦентрКредит» АҚ",
    )


@pytest.mark.django_db
def test_business_registration_creates_company_and_single_admin(registration_references):
    client = APIClient()
    response = client.post(
        "/api/auth/register/",
        registration_payload(registration_references),
        format="json",
    )

    assert response.status_code == 201
    assert settings.AUTH_TOKEN_COOKIE_NAME not in response.cookies
    organization = Organization.objects.get(bin="123456789012")
    assert organization.actual_address == organization.legal_address
    assert organization.bank == registration_references
    assert organization.kbe == "17"
    assert organization.iik == "KZ168562203138317128"
    assert (
        User.objects.filter(organization=organization, role=User.Role.BUSINESS_ADMIN).count() == 1
    )
    assert not Token.objects.filter(user__organization=organization).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("duplicate_field", ["bin", "iik", "email"])
def test_business_registration_rejects_duplicate_identity_or_bank_account(
    registration_references, duplicate_field
):
    first = registration_payload(registration_references)
    assert APIClient().post("/api/auth/register/", first, format="json").status_code == 201
    second = registration_payload(registration_references)
    second["bin"] = "123456789013"
    second["email"] = "other@example.test"
    second["iik"] = "KZ868562203138317129"
    if duplicate_field == "bin":
        second["bin"] = first["bin"]
    elif duplicate_field == "iik":
        second["iik"] = first["iik"]
    else:
        second["email"] = "ADMIN@EXAMPLE.TEST"

    response = APIClient().post("/api/auth/register/", second, format="json")

    assert response.status_code == 400
    assert duplicate_field in response.data
    assert Organization.objects.filter(kind=Organization.Kind.BUSINESS).count() == 1
    assert User.objects.filter(role=User.Role.BUSINESS_ADMIN).count() == 1


@pytest.mark.django_db
def test_user_email_is_unique_case_insensitively_at_database_level(enbek, make_user):
    make_user(User.Role.ENBEK_ADMIN, enbek, "unique@example.test")

    with pytest.raises(IntegrityError), transaction.atomic():
        make_user(User.Role.ENBEK_EXECUTOR, enbek, "UNIQUE@EXAMPLE.TEST")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bin", "1234ABC89012"),
        ("bin", "12345678901"),
        ("director_iin", "00000000000"),
        ("kbe", "37"),
        ("iik", "KZ008562203138317128"),
        ("oked_code", "99999"),
    ],
)
def test_business_registration_rejects_invalid_requisites(registration_references, field, value):
    payload = registration_payload(registration_references)
    payload[field] = value

    response = APIClient().post("/api/auth/register/", payload, format="json")

    assert response.status_code == 400
    assert field in response.data


@pytest.mark.django_db
def test_reference_directories_are_public(registration_references):
    client = APIClient()

    oked_response = client.get("/api/organizations/oked/")
    bank_response = client.get("/api/organizations/banks/")

    assert oked_response.status_code == 200
    assert oked_response.data[0]["code"] == "41201"
    assert bank_response.status_code == 200
    assert bank_response.data[0]["bic"] == registration_references.bic


@pytest.mark.django_db
def test_business_requisites_are_validated_when_profile_is_edited(
    business, registration_references
):
    business.bank = registration_references
    business.kbe = "17"
    business.iik = "KZ168562203138317128"
    business.save()

    serializer = OrganizationSerializer(
        business,
        data={"iik": "KZ008562203138317128"},
        partial=True,
    )

    assert not serializer.is_valid()
    assert "iik" in serializer.errors


@pytest.mark.django_db
def test_business_cannot_change_profile_to_another_company_bank_account(
    business, registration_references
):
    business.bank = registration_references
    business.kbe = "17"
    business.iik = "KZ868562203138317129"
    business.save(update_fields=["bank", "kbe", "iik", "updated_at"])
    assert APIClient().post(
        "/api/auth/register/", registration_payload(registration_references), format="json"
    ).status_code == 201

    serializer = OrganizationSerializer(
        business, data={"iik": "KZ168562203138317128"}, partial=True
    )

    assert not serializer.is_valid()
    assert "iik" in serializer.errors
