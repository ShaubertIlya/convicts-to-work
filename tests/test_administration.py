import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organizations.models import Organization


@pytest.mark.django_db
def test_enbek_staff_can_list_businesses_but_business_sees_only_itself(
    business, enbek, make_user
):
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek, "executor@enbek.example.test")
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business, "admin@business.example.test")
    client = APIClient()

    client.force_authenticate(executor)
    response = client.get("/api/organizations/", {"kind": "BUSINESS"})
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(business.id)

    client.force_authenticate(business_admin)
    response = client.get("/api/organizations/")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(business.id)


@pytest.mark.django_db
def test_enbek_admin_manages_platform_users_and_cannot_block_self(
    business, enbek, make_user
):
    admin = make_user(User.Role.ENBEK_ADMIN, enbek, "admin@enbek.example.test")
    executor = make_user(User.Role.ENBEK_EXECUTOR, enbek, "executor@enbek.example.test")
    business_admin = make_user(User.Role.BUSINESS_ADMIN, business, "admin@business.example.test")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.get("/api/auth/users/")
    assert response.status_code == 200
    assert response.data["count"] == 3

    response = client.patch(
        f"/api/auth/users/{business_admin.id}/",
        {"is_active": False},
        format="json",
    )
    assert response.status_code == 200
    business_admin.refresh_from_db()
    assert not business_admin.is_active

    response = client.patch(
        f"/api/auth/users/{admin.id}/",
        {"is_active": False},
        format="json",
    )
    assert response.status_code == 400
    admin.refresh_from_db()
    assert admin.is_active

    client.force_authenticate(executor)
    response = client.get("/api/auth/users/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_enbek_admin_creates_user_for_selected_organization(enbek, make_user):
    admin = make_user(User.Role.ENBEK_ADMIN, enbek, "admin@enbek.example.test")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        "/api/auth/users/",
        {
            "email": "medic-new@enbek.example.test",
            "password": "Temporary-123",
            "full_name": "Новый Медик",
            "role": User.Role.MEDIC,
            "organization": str(enbek.id),
            "is_active": True,
        },
        format="json",
    )

    assert response.status_code == 201
    assert User.objects.filter(
        email="medic-new@enbek.example.test",
        role=User.Role.MEDIC,
        organization=enbek,
    ).exists()


@pytest.mark.django_db
def test_admin_cannot_reuse_another_user_email_with_different_case(enbek, make_user):
    admin = make_user(User.Role.ENBEK_ADMIN, enbek, "admin@enbek.example.test")
    medic = make_user(User.Role.MEDIC, enbek, "medic@enbek.example.test")
    client = APIClient()
    client.force_authenticate(admin)

    created = client.post("/api/auth/users/", {
        "email": "MEDIC@ENBEK.EXAMPLE.TEST", "password": "Temporary-123",
        "full_name": "Новый Медик", "role": User.Role.MEDIC,
        "organization": str(enbek.id),
    }, format="json")
    updated = client.patch(f"/api/auth/users/{medic.id}/", {
        "email": "ADMIN@ENBEK.EXAMPLE.TEST",
    }, format="json")

    assert created.status_code == 400
    assert "email" in created.data
    assert updated.status_code == 400
    assert "email" in updated.data


@pytest.mark.django_db
def test_user_and_organization_registries_show_ten_rows_per_page(
    business, enbek, make_user
):
    admin = make_user(User.Role.ENBEK_ADMIN, enbek, "admin@enbek.example.test")
    for index in range(10):
        make_user(
            User.Role.ENBEK_EXECUTOR,
            enbek,
            f"executor-{index}@enbek.example.test",
        )
        Organization.objects.create(
            name=f"Тестовое ТОО {index}",
            kind=Organization.Kind.BUSINESS,
            bin=f"{index + 3:012d}",
            activity_type=business.activity_type,
            staff_count=business.staff_count,
            legal_address=business.legal_address,
            actual_address=business.actual_address,
            oked_code=business.oked_code,
            director_full_name=business.director_full_name,
            director_iin=business.director_iin,
            director_position=business.director_position,
            director_email=business.director_email,
            director_phone=business.director_phone,
        )

    client = APIClient()
    client.force_authenticate(admin)
    for path in ("/api/auth/users/", "/api/organizations/?kind=BUSINESS"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.data["count"] == 11
        assert len(response.data["results"]) == 10
        assert response.data["next"] is not None
