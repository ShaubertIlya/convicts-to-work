from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from apps.core.models import TimeStampedModel


class OkedCode(TimeStampedModel):
    code = models.CharField(max_length=16, unique=True)
    name_ru = models.CharField(max_length=500)
    name_kk = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name_ru}"


class Bank(TimeStampedModel):
    bic = models.CharField(
        max_length=8,
        unique=True,
        validators=[RegexValidator(r"^[A-Z0-9]{8}$", "БИК должен содержать 8 символов")],
    )
    bank_code = models.CharField(
        max_length=3,
        validators=[RegexValidator(r"^\d{3}$", "Код банка должен содержать 3 цифры")],
    )
    name_ru = models.CharField(max_length=500)
    name_kk = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_ru"]

    def __str__(self) -> str:
        return f"{self.name_ru} ({self.bic})"


class Organization(TimeStampedModel):
    class Kind(models.TextChoices):
        BUSINESS = "BUSINESS", "МСБ"
        ENBEK = "ENBEK", "РГП Еңбек"

    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.BUSINESS)
    bin = models.CharField(
        max_length=12,
        unique=True,
        validators=[RegexValidator(r"^\d{12}$", "БИН должен содержать 12 цифр")],
    )
    activity_type = models.CharField(max_length=255)
    staff_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    legal_address = models.CharField(max_length=500)
    actual_address = models.CharField(max_length=500)
    actual_address_same = models.BooleanField(default=False)
    oked_code = models.CharField(max_length=16)
    bank_details = models.TextField(blank=True)
    bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        related_name="organizations",
        null=True,
        blank=True,
    )
    kbe = models.CharField(
        max_length=2,
        blank=True,
        validators=[RegexValidator(r"^[12]\d$", "КБЕ должен содержать 2 цифры")],
    )
    iik = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                r"^KZ\d{2}[A-HJ-NP-Z0-9]{16}$",
                "ИИК должен быть казахстанским IBAN из 20 символов",
            )
        ],
    )
    licenses = models.TextField(blank=True)
    director_full_name = models.CharField(max_length=255)
    director_iin = models.CharField(
        max_length=12,
        validators=[RegexValidator(r"^\d{12}$", "ИИН должен содержать 12 цифр")],
    )
    director_position = models.CharField(max_length=255)
    director_email = models.EmailField()
    director_phone = models.CharField(max_length=32)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if self.actual_address_same:
            self.actual_address = self.legal_address
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
