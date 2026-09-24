from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ContractSequence(models.Model):
    year = models.PositiveSmallIntegerField(primary_key=True)
    last_value = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.year}: {self.last_value}"


class EmploymentContract(TimeStampedModel):
    class Status(models.TextChoices):
        AWAITING_PRISONER = "AWAITING_PRISONER", "Ожидает подписи осуждённого"
        PARTIALLY_SIGNED = "PARTIALLY_SIGNED", "Подписан частично"
        ACTIVE = "ACTIVE", "Действующий"
        EXPIRED = "EXPIRED", "Истёк"

    number = models.CharField(max_length=24, unique=True)
    application = models.ForeignKey(
        "applications.JobApplication", on_delete=models.PROTECT, related_name="contracts"
    )
    candidate = models.OneToOneField(
        "applications.CandidateProposal", on_delete=models.PROTECT, related_name="contract"
    )
    prisoner = models.ForeignKey(
        "prisoners.Prisoner", on_delete=models.PROTECT, related_name="contracts"
    )
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="contracts"
    )
    organization_snapshot = models.JSONField(default=dict, blank=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.AWAITING_PRISONER
    )
    document = models.FileField(upload_to="contracts/", blank=True)
    document_hash = models.CharField(max_length=64, blank=True)
    document_version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__gt=models.F("starts_on")),
                name="contract_end_after_start",
            )
        ]


class ContractSignature(TimeStampedModel):
    class Party(models.TextChoices):
        PRISONER = "PRISONER", "Осуждённый"
        ENBEK_MANAGER = "ENBEK_MANAGER", "Руководитель Еңбек"
        BUSINESS_ADMIN = "BUSINESS_ADMIN", "МСБ"

    class Method(models.TextChoices):
        BIOMETRY = "BIOMETRY", "Биометрия"
        BUTTON = "BUTTON", "Подтверждение кнопкой"

    contract = models.ForeignKey(
        EmploymentContract, on_delete=models.CASCADE, related_name="signatures"
    )
    party = models.CharField(max_length=24, choices=Party.choices)
    method = models.CharField(max_length=16, choices=Method.choices)
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="contract_signatures",
        help_text="Сотрудник, инициировавший биометрию, либо нажавший кнопку.",
    )
    signed_at = models.DateTimeField()
    evidence = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["contract", "party"], name="unique_contract_party")
        ]


class BiometricSignatureAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Ожидает"
        VERIFIED = "VERIFIED", "Подтверждена"
        FAILED = "FAILED", "Не пройдена"
        EXPIRED = "EXPIRED", "Истекла"

    contract = models.ForeignKey(
        EmploymentContract, on_delete=models.CASCADE, related_name="biometric_attempts"
    )
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    state_digest = models.CharField(max_length=64, unique=True)
    verification_id = models.CharField(max_length=128, unique=True)
    contract_version = models.PositiveIntegerField(default=1)
    contract_digest = models.CharField(max_length=64, default="")
    consent_acknowledged_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
