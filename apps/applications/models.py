from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class JobApplication(TimeStampedModel):
    class SkillRequirement(models.TextChoices):
        REQUIRED = "REQUIRED", "Только с навыком"
        TRAINING_ALLOWED = "TRAINING_ALLOWED", "Возможно обучение"

    class EmploymentType(models.TextChoices):
        FULL = "FULL", "Полная занятость"
        PART_TIME = "PART_TIME", "Частичная занятость"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Черновик"
        SUBMITTED = "SUBMITTED", "Подана"
        PROPOSED = "PROPOSED", "Кандидаты предложены"
        BUSINESS_RESPONDED = "BUSINESS_RESPONDED", "Ответ МСБ получен"
        APPROVED = "APPROVED", "Согласована Еңбек"
        REJECTED_BUSINESS = "REJECTED_BUSINESS", "Отклонено по инициативе заявителя"
        REJECTED_ENBEK = "REJECTED_ENBEK", "Отклонено по инициативе Еңбек"
        SCREENING = "SCREENING", "Обследование"
        CONTRACTING = "CONTRACTING", "Заключение договоров"
        COMPLETED = "COMPLETED", "Завершена"
        WITHDRAWN = "WITHDRAWN", "Отозвана"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="applications"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_applications"
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    skill = models.ForeignKey("prisoners.Skill", on_delete=models.PROTECT)
    skill_requirement = models.CharField(max_length=24, choices=SkillRequirement.choices)
    workplace_address = models.CharField(max_length=500)
    salary = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    duration_months = models.PositiveSmallIntegerField(default=12, editable=False)
    schedule = models.CharField(max_length=255)
    employment_type = models.CharField(max_length=16, choices=EmploymentType.choices)
    activity_description = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    business_comment = models.TextField(blank=True)
    enbek_comment = models.TextField(blank=True)
    organization_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class CandidateProposal(TimeStampedModel):
    class Status(models.TextChoices):
        PROPOSED = "PROPOSED", "Предложен"
        BUSINESS_ACCEPTED = "BUSINESS_ACCEPTED", "Выбран МСБ"
        BUSINESS_REJECTED = "BUSINESS_REJECTED", "Не выбран МСБ"
        ENBEK_APPROVED = "ENBEK_APPROVED", "Согласован Еңбек"
        ENBEK_REJECTED = "ENBEK_REJECTED", "Отклонён Еңбек"
        MEDICAL_PENDING = "MEDICAL_PENDING", "Ожидает медосмотр"
        MEDICAL_PASSED = "MEDICAL_PASSED", "Медосмотр пройден"
        MEDICAL_FAILED = "MEDICAL_FAILED", "Медицинский отказ"
        PSYCHOLOGICAL_PENDING = "PSYCHOLOGICAL_PENDING", "Ожидает психолога"
        PSYCHOLOGICAL_PASSED = "PSYCHOLOGICAL_PASSED", "Психолог пройден"
        PSYCHOLOGICAL_FAILED = "PSYCHOLOGICAL_FAILED", "Отказ психолога"
        READY_FOR_CONTRACT = "READY_FOR_CONTRACT", "Готов к договору"
        CONTRACT_CREATED = "CONTRACT_CREATED", "Договор создан"

    application = models.ForeignKey(
        JobApplication, on_delete=models.CASCADE, related_name="candidates"
    )
    prisoner = models.ForeignKey(
        "prisoners.Prisoner", on_delete=models.PROTECT, related_name="proposals"
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PROPOSED)
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-prisoner__rating", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "prisoner"], name="unique_application_candidate"
            )
        ]


class Screening(TimeStampedModel):
    class Kind(models.TextChoices):
        MEDICAL = "MEDICAL", "Медицинское обследование"
        PSYCHOLOGICAL = "PSYCHOLOGICAL", "Психологическое обследование"

    class Result(models.TextChoices):
        PENDING = "PENDING", "Ожидает заключения"
        APPROVED = "APPROVED", "Согласовано"
        REJECTED = "REJECTED", "Отклонено"

    candidate = models.ForeignKey(
        CandidateProposal, on_delete=models.CASCADE, related_name="screenings"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    result = models.CharField(max_length=16, choices=Result.choices, default=Result.PENDING)
    comment = models.TextField(blank=True)
    conclusion_document = models.FileField(
        upload_to="screenings/conclusions/%Y/%m/",
        blank=True,
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="screenings",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["candidate", "kind"], name="unique_candidate_screening")
        ]
