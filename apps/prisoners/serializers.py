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
            "has_active_contracts",
            "change_history",
        )


class BusinessCandidateSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = Prisoner
        fields = ("id", "photo", "rating", "skills")
