from django.conf import settings
from django.contrib.auth import logout
from django.db import IntegrityError
from rest_framework import filters, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import RegistryPagination

from .models import User
from .serializers import (
    BusinessRegistrationSerializer,
    EnbekUserCreateSerializer,
    LoginSerializer,
    UserSerializer,
)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        response = Response(UserSerializer(user).data)
        response.set_cookie(
            settings.AUTH_TOKEN_COOKIE_NAME,
            token.key,
            max_age=settings.AUTH_TOKEN_MAX_AGE,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            path="/",
        )
        return response


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        logout(request)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.AUTH_TOKEN_COOKIE_NAME,
            samesite="Lax",
            path="/",
        )
        return response


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class BusinessRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = BusinessRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = serializer.save()
        except IntegrityError as exc:
            raise ValidationError(
                "БИН, ИИК или email уже используется в системе. Проверьте введённые данные."
            ) from exc
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class EnbekUserViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RegistryPagination
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "email", "organization__name", "organization__bin"]
    ordering_fields = ["full_name", "date_joined", "email"]
    ordering = ["full_name"]

    def get_queryset(self):
        if self.request.user.role != User.Role.ENBEK_ADMIN:
            return User.objects.none()
        queryset = User.objects.select_related("organization")
        if role := self.request.query_params.get("role"):
            queryset = queryset.filter(role=role)
        if organization := self.request.query_params.get("organization"):
            queryset = queryset.filter(organization_id=organization)
        if active := self.request.query_params.get("is_active"):
            queryset = queryset.filter(is_active=active.lower() == "true")
        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "partial_update"}:
            return EnbekUserCreateSerializer
        return UserSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.role != User.Role.ENBEK_ADMIN:
            raise PermissionDenied("Управление пользователями доступно администратору Еңбек.")
