from django.conf import settings
from rest_framework.authentication import SessionAuthentication, TokenAuthentication


class CookieTokenAuthentication(TokenAuthentication):
    """Authenticate API requests from an HttpOnly token cookie.

    Header-based token authentication remains available for service clients. Cookie
    authentication also enforces CSRF because browsers attach the cookie automatically.
    """

    def authenticate(self, request):
        header_result = super().authenticate(request)
        if header_result is not None:
            return header_result

        token = request.COOKIES.get(settings.AUTH_TOKEN_COOKIE_NAME)
        if not token:
            return None

        result = self.authenticate_credentials(token)
        SessionAuthentication().enforce_csrf(request)
        return result
