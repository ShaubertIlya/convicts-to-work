import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.mark.django_db
def test_login_persists_http_only_token_and_logout_revokes_it(enbek, make_user, settings):
    user = make_user(User.Role.ENBEK_ADMIN, enbek, "admin@enbek.example.test")
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/csrf/")
    csrf_token = client.cookies["csrftoken"].value

    login_response = client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "Test-password-123"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert login_response.status_code == 200
    auth_cookie = login_response.cookies[settings.AUTH_TOKEN_COOKIE_NAME]
    assert auth_cookie["httponly"] is True
    assert auth_cookie["samesite"] == "Lax"
    assert Token.objects.filter(user=user, key=auth_cookie.value).exists()
    assert client.get("/api/auth/me/").status_code == 200

    logout_response = client.post(
        "/api/auth/logout/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert logout_response.status_code == 204
    assert not Token.objects.filter(user=user).exists()
    assert logout_response.cookies[settings.AUTH_TOKEN_COOKIE_NAME]["max-age"] == 0


@pytest.mark.django_db
def test_protected_endpoint_redirect_source_is_unauthorized_without_token():
    response = APIClient().get("/api/auth/me/")

    assert response.status_code == 401
