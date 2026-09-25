from uuid import UUID

from django.db import transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from .models import Prisoner, PrisonerChangeHistory, Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "name_ru", "name_kk", "is_active")


class PrisonerChangeHistorySerializer(serializers.ModelSerializer):
    change_type_label = serializers.CharField(source="get_change_type_display", read_only=True)

    class Meta:
        model = PrisonerChangeHistory
        fields = (
            "id",
            "change_type",
            "change_type_label",
            "effective_date",
            "previous_value",
            "new_value",
            "note",
        )


class PrisonerSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.JSONField(write_only=True, required=False)
    is_available = serializers.BooleanField(required=False, default=True)
    has_active_contracts = serializers.BooleanField(read_only=True)
    change_history = PrisonerChangeHistorySerializer(many=True, read_only=True)
    disability_status_label = serializers.CharField(
        source="get_disability_status_display", read_only=True
    )
    pension_status_label = serializers.CharField(
        source="get_pension_status_display", read_only=True
    )
    work_capacity_label = serializers.CharField(
        source="get_work_capacity_display", read_only=True
    )

    class Meta:
        model = Prisoner
        fields = (
            "id",
            "full_name",
            "iin",
            "birth_date",
            "photo",
            "rating",
            "is_available",
            "work_capacity",
            "work_capacity_label",
            "criminal_article",
            "sentence_term",
            "sentence_start",
            "sentence_end",
            "education",
            "qualification",
            "pre_prison_experience",
            "pre_prison_experience_years",
            "penitentiary_education",
            "health_status",
            "disability_status",
            "disability_status_label",
            "medical_restrictions",
            "current_employment",
            "total_work_experience_years",
            "pension_status",
            "pension_status_label",
            "disciplinary_restrictions",
            "safety_briefing_info",
            "skills",
            "skill_ids",
            "has_active_contracts",
            "change_history",
        )

    def validate_iin(self, value):
        if len(value) != 12 or not value.isascii() or not value.isdigit():
            raise serializers.ValidationError("ИИН должен содержать ровно 12 цифр")
        return value

    def validate_birth_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Дата рождения не может быть в будущем")
        return value

    def validate_photo(self, value):
        if value.size > 8 * 1024 * 1024:
            raise serializers.ValidationError("Фото не должно превышать 8 МБ")
        try:
            with Image.open(value) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise serializers.ValidationError("Загрузите фото в формате JPEG или PNG")
                if max(image.size) > 5000 or image.width * image.height > 16_000_000:
                    raise serializers.ValidationError("Размер фото слишком большой")
                image.verify()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise serializers.ValidationError("Не удалось прочитать фото") from exc
        finally:
            value.seek(0)
        return value

    def validate_skill_ids(self, value):
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError("Передайте список идентификаторов навыков")
        try:
            identifiers = [UUID(item) for item in value]
        except ValueError as exc:
            raise serializers.ValidationError("Некорректный идентификатор навыка") from exc
        if len(identifiers) != len(set(identifiers)):
            raise serializers.ValidationError("Навыки не должны повторяться")
        skills = list(Skill.objects.filter(id__in=identifiers, is_active=True))
        if len(skills) != len(identifiers):
            raise serializers.ValidationError("Один или несколько навыков не найдены")
        return skills

    def validate(self, attrs):
        start = attrs.get("sentence_start", getattr(self.instance, "sentence_start", None))
        end = attrs.get("sentence_end", getattr(self.instance, "sentence_end", None))
        if start and end and end < start:
            raise serializers.ValidationError({"sentence_end": "Окончание срока раньше его начала"})
        for field in ("pre_prison_experience_years", "total_work_experience_years"):
            years = attrs.get(field)
            if years is not None and years > 100:
                raise serializers.ValidationError({field: "Стаж не может превышать 100 лет"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        skills = validated_data.pop("skill_ids", [])
        prisoner = super().create(validated_data)
        prisoner.skills.set(skills)
        return prisoner

    @transaction.atomic
    def update(self, instance, validated_data):
        skills = validated_data.pop("skill_ids", None)
        tracked = {
            "qualification": PrisonerChangeHistory.ChangeType.QUALIFICATION,
            "health_status": PrisonerChangeHistory.ChangeType.HEALTH,
            "current_employment": PrisonerChangeHistory.ChangeType.EMPLOYMENT,
        }
        changes = [
            (change_type, getattr(instance, field), validated_data[field])
            for field, change_type in tracked.items()
            if field in validated_data and getattr(instance, field) != validated_data[field]
        ]
        prisoner = super().update(instance, validated_data)
        if skills is not None:
            prisoner.skills.set(skills)
        for change_type, previous, current in changes:
            PrisonerChangeHistory.objects.create(
                prisoner=prisoner,
                change_type=change_type,
                effective_date=timezone.localdate(),
                previous_value=previous,
                new_value=current,
            )
        return prisoner


class BusinessCandidateSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = Prisoner
        fields = ("id", "photo", "rating", "skills")
