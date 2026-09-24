from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from apps.core.models import TimeStampedModel

from .storage import prisoner_photo_storage


class Skill(TimeStampedModel):
    name_ru = models.CharField(max_length=120, unique=True)
    name_kk = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_ru"]

    def __str__(self) -> str:
        return self.name_ru


class Prisoner(TimeStampedModel):
    class WorkCapacity(models.TextChoices):
        UNKNOWN = "UNKNOWN", "Не установлено"
        CAPABLE = "CAPABLE", "Трудоспособен"
        UNABLE = "UNABLE", "Нетрудоспособен"

    class DisabilityStatus(models.TextChoices):
        NONE = "NONE", "Нет инвалидности"
        GROUP_1 = "GROUP_1", "I группа"
        GROUP_2 = "GROUP_2", "II группа"
        GROUP_3 = "GROUP_3", "III группа"

    class PensionStatus(models.TextChoices):
        NONE = "NONE", "Не является пенсионером"
        AGE = "AGE", "По возрасту"
        DISABILITY = "DISABILITY", "По инвалидности"
        OTHER = "OTHER", "Иное основание"

    full_name = models.CharField(max_length=255)
    iin = models.CharField(
        max_length=12,
        unique=True,
        validators=[RegexValidator(r"^\d{12}$", "ИИН должен содержать 12 цифр")],
    )
    birth_date = models.DateField()
    photo = models.ImageField(
        upload_to="prisoners/reference/", storage=prisoner_photo_storage, blank=True
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    is_available = models.BooleanField(default=True)
    work_capacity = models.CharField(
        max_length=16, choices=WorkCapacity.choices, default=WorkCapacity.UNKNOWN
    )
    criminal_article = models.CharField(max_length=255, blank=True)
    sentence_term = models.CharField(max_length=120, blank=True)
    sentence_start = models.DateField(null=True, blank=True)
    sentence_end = models.DateField(null=True, blank=True)
    education = models.CharField(max_length=255, blank=True)
    qualification = models.CharField(max_length=255, blank=True)
    pre_prison_experience = models.TextField(blank=True)
    pre_prison_experience_years = models.PositiveSmallIntegerField(default=0)
    penitentiary_education = models.TextField(blank=True)
    health_status = models.CharField(max_length=255, blank=True)
    disability_status = models.CharField(
        max_length=16, choices=DisabilityStatus.choices, default=DisabilityStatus.NONE
    )
    medical_restrictions = models.TextField(blank=True)
    current_employment = models.CharField(max_length=255, blank=True)
    total_work_experience_years = models.PositiveSmallIntegerField(default=0)
    pension_status = models.CharField(
        max_length=16, choices=PensionStatus.choices, default=PensionStatus.NONE
    )
    disciplinary_restrictions = models.TextField(blank=True)
    safety_briefing_info = models.TextField(blank=True)
    skills = models.ManyToManyField(Skill, through="PrisonerSkill", related_name="prisoners")

    class Meta:
        ordering = ["-rating", "full_name"]

    def __str__(self) -> str:
        return self.full_name


class PrisonerSkill(TimeStampedModel):
    prisoner = models.ForeignKey(Prisoner, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["prisoner", "skill"], name="unique_prisoner_skill")
        ]


class PrisonerChangeHistory(TimeStampedModel):
    class ChangeType(models.TextChoices):
        QUALIFICATION = "QUALIFICATION", "Квалификация"
        HEALTH = "HEALTH", "Состояние здоровья"
        EMPLOYMENT = "EMPLOYMENT", "Трудовая занятость"

    prisoner = models.ForeignKey(Prisoner, on_delete=models.CASCADE, related_name="change_history")
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    effective_date = models.DateField()
    previous_value = models.TextField(blank=True)
    new_value = models.TextField()
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-effective_date", "-created_at"]
