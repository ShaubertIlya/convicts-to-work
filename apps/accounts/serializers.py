from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.organizations.models import Bank, OkedCode, Organization
from apps.organizations.validators import is_valid_kz_iik

from .models import User


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_kind = serializers.CharField(source="organization.kind", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "organization",
            "organization_name",
            "organization_kind",
            "is_active",
            "date_joined",
        )
        read_only_fields = fields


class EnbekUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(min_length=10, write_only=True, required=False)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), required=False
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "password",
            "full_name",
            "role",
            "organization",
            "is_active",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        request = self.context["request"]
        organization = attrs.get(
            "organization",
            self.instance.organization if self.instance else request.user.organization,
        )
        role = attrs.get("role", self.instance.role if self.instance else None)
        if not organization:
            raise serializers.ValidationError({"organization": "Выберите организацию."})
        if organization.kind == Organization.Kind.BUSINESS and role != User.Role.BUSINESS_ADMIN:
            raise serializers.ValidationError(
                {"role": "В организации МСБ доступна только роль администратора МСБ."}
            )
        if organization.kind == Organization.Kind.ENBEK and role == User.Role.BUSINESS_ADMIN:
            raise serializers.ValidationError(
                {"role": "Роль администратора МСБ недоступна в организации Еңбек."}
            )
        if self.instance == request.user:
            if attrs.get("is_active") is False:
                raise serializers.ValidationError(
                    {"is_active": "Нельзя заблокировать собственную учётную запись."}
                )
            if role != User.Role.ENBEK_ADMIN:
                raise serializers.ValidationError(
                    {"role": "Нельзя снять с себя роль администратора Еңбек."}
                )
        attrs["organization"] = organization
        return attrs

    def create(self, validated_data):
        if not validated_data.get("password"):
            raise serializers.ValidationError({"password": "Пароль обязателен."})
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )
        if user is None or not user.is_active:
            raise serializers.ValidationError("Неверный email или пароль.")
        attrs["user"] = user
        return attrs


class BusinessRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=10, max_length=128, write_only=True)
    full_name = serializers.CharField(min_length=2, max_length=255)
    name = serializers.CharField(min_length=2, max_length=255)
    bin = serializers.RegexField(
        r"^\d{12}$", error_messages={"invalid": "БИН должен содержать ровно 12 цифр."}
    )
    activity_type = serializers.CharField(min_length=2, max_length=255)
    staff_count = serializers.IntegerField(min_value=1, max_value=1_000_000)
    legal_address = serializers.CharField(min_length=5, max_length=500)
    actual_address = serializers.CharField(
        min_length=5, max_length=500, allow_blank=True, required=False
    )
    actual_address_same = serializers.BooleanField(default=False)
    oked_code = serializers.RegexField(
        r"^\d{5}$", error_messages={"invalid": "Выберите пятизначный код ОКЭД."}
    )
    bank = serializers.PrimaryKeyRelatedField(queryset=Bank.objects.filter(is_active=True))
    kbe = serializers.RegexField(
        r"^[12]\d$",
        error_messages={
            "invalid": "КБЕ должен содержать 2 цифры; первая — 1 (резидент) или 2 (нерезидент)."
        },
    )
    iik = serializers.RegexField(
        r"^KZ\d{2}[A-HJ-NP-Z0-9]{16}$",
        error_messages={"invalid": "ИИК должен начинаться с KZ и содержать 20 символов."},
    )
    licenses = serializers.CharField(max_length=2000, allow_blank=True, required=False)
    director_full_name = serializers.CharField(min_length=2, max_length=255)
    director_iin = serializers.RegexField(
        r"^\d{12}$", error_messages={"invalid": "ИИН должен содержать ровно 12 цифр."}
    )
    director_position = serializers.CharField(min_length=2, max_length=255)
    director_email = serializers.EmailField()
    director_phone = serializers.RegexField(
        r"^\+7\d{10}$",
        error_messages={"invalid": "Телефон должен быть указан в формате +7 и 10 цифр."},
    )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value

    def validate_password(self, value):
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Пароль должен содержать буквы и цифры.")
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value

    def validate_bin(self, value):
        if Organization.objects.filter(bin=value).exists():
            raise serializers.ValidationError("Организация с таким БИН уже существует.")
        return value

    def validate_oked_code(self, value):
        if not OkedCode.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Выберите код из справочника ОКЭД.")
        return value

    def validate_iik(self, value):
        if not is_valid_kz_iik(value):
            raise serializers.ValidationError("Контрольная сумма ИИК некорректна.")
        return value

    def validate(self, attrs):
        if not attrs["actual_address_same"] and not attrs.get("actual_address"):
            raise serializers.ValidationError({"actual_address": "Укажите фактический адрес."})
        if attrs["actual_address_same"]:
            attrs["actual_address"] = attrs["legal_address"]
        if attrs["iik"][4:7] != attrs["bank"].bank_code:
            raise serializers.ValidationError(
                {"iik": "Код банка в ИИК не соответствует выбранному банку."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user_fields = {key: validated_data.pop(key) for key in ("email", "password", "full_name")}
        organization = Organization.objects.create(
            kind=Organization.Kind.BUSINESS, **validated_data
        )
        return User.objects.create_user(
            organization=organization,
            role=User.Role.BUSINESS_ADMIN,
            **user_fields,
        )
