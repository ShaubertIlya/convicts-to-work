from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ENBEK_ADMIN)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        BUSINESS_ADMIN = "BUSINESS_ADMIN", "Администратор МСБ"
        ENBEK_ADMIN = "ENBEK_ADMIN", "Администратор Еңбек"
        ENBEK_MANAGER = "ENBEK_MANAGER", "Руководитель Еңбек"
        ENBEK_EXECUTOR = "ENBEK_EXECUTOR", "Исполнитель Еңбек"
        MEDIC = "MEDIC", "Медик"
        PSYCHOLOGIST = "PSYCHOLOGIST", "Психолог"

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=32, choices=Role.choices)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]
    objects = UserManager()

    def __str__(self) -> str:
        return self.full_name or self.email
