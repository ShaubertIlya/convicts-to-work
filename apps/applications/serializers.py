from rest_framework import serializers
from rest_framework.fields import DecimalField, IntegerField

from apps.organizations.snapshots import build_organization_snapshot
from apps.prisoners.serializers import BusinessCandidateSerializer, PrisonerSerializer

from .models import CandidateProposal, JobApplication, Screening


class ScreeningSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)
    application_id = serializers.UUIDField(source="candidate.application_id", read_only=True)
    prisoner_name = serializers.CharField(source="candidate.prisoner.full_name", read_only=True)
    organization_name = serializers.CharField(
        source="candidate.application.organization.name", read_only=True
    )
    skill_name_ru = serializers.CharField(
        source="candidate.application.skill.name_ru", read_only=True
    )
    workplace_address = serializers.CharField(
        source="candidate.application.workplace_address", read_only=True
    )
    schedule = serializers.CharField(source="candidate.application.schedule", read_only=True)
    conclusion_file_name = serializers.SerializerMethodField()

    def get_conclusion_file_name(self, obj):
        if not obj.conclusion_document:
            return ""
        return obj.conclusion_document.name.rsplit("/", 1)[-1]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request and request.user.role == request.user.Role.BUSINESS_ADMIN:
            # The business tracks screening progress, but personal medical data
            # and the prisoner's identity are not disclosed before a contract.
            for field in (
                "prisoner_name", "comment", "conclusion_document",
                "conclusion_file_name", "reviewer_name",
            ):
                data.pop(field, None)
        return data

    class Meta:
        model = Screening
        fields = (
            "id",
            "application_id",
            "prisoner_name",
            "organization_name",
            "skill_name_ru",
            "workplace_address",
            "schedule",
            "kind",
            "result",
            "comment",
            "conclusion_document",
            "conclusion_file_name",
            "reviewer_name",
            "reviewed_at",
            "created_at",
        )
        read_only_fields = fields


class CandidateProposalSerializer(serializers.ModelSerializer):
    prisoner = serializers.SerializerMethodField()
    screenings = ScreeningSerializer(many=True, read_only=True)

    class Meta:
        model = CandidateProposal
        fields = ("id", "prisoner", "status", "screenings", "created_at")

    def get_prisoner(self, obj):
        request = self.context.get("request")
        if request and request.user.role == request.user.Role.BUSINESS_ADMIN:
            return BusinessCandidateSerializer(obj.prisoner, context=self.context).data
        return PrisonerSerializer(obj.prisoner, context=self.context).data


class JobApplicationSerializer(serializers.ModelSerializer):
    quantity = IntegerField(min_value=1, max_value=1000)
    salary = DecimalField(max_digits=14, decimal_places=2, min_value=1, max_value=1_000_000_000)
    workplace_address = serializers.CharField(min_length=5, max_length=500)
    schedule = serializers.CharField(min_length=2, max_length=255)
    activity_description = serializers.CharField(min_length=10, max_length=2000)
    candidates = CandidateProposalSerializer(many=True, read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_details = serializers.SerializerMethodField()
    skill_name_ru = serializers.CharField(source="skill.name_ru", read_only=True)
    skill_name_kk = serializers.CharField(source="skill.name_kk", read_only=True)

    class Meta:
        model = JobApplication
        fields = "__all__"
        read_only_fields = (
            "id",
            "organization",
            "created_by",
            "duration_months",
            "status",
            "business_comment",
            "enbek_comment",
            "created_at",
            "updated_at",
            "organization_snapshot",
        )

    def get_organization_details(self, obj):
        return obj.organization_snapshot or build_organization_snapshot(obj.organization)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        clinical_kinds = {
            request.user.Role.MEDIC: Screening.Kind.MEDICAL,
            request.user.Role.PSYCHOLOGIST: Screening.Kind.PSYCHOLOGICAL,
        } if request else {}
        kind = clinical_kinds.get(request.user.role) if request else None
        if kind:
            data.pop("organization_snapshot", None)
            data.pop("organization_details", None)
            candidates = []
            for candidate in data["candidates"]:
                candidate["screenings"] = [
                    screening for screening in candidate["screenings"]
                    if screening["kind"] == kind
                ]
                if candidate["screenings"]:
                    candidates.append(candidate)
            data["candidates"] = candidates
        return data

    def validate(self, attrs):
        if self.instance and self.instance.status != JobApplication.Status.DRAFT:
            raise serializers.ValidationError("Редактировать можно только черновик заявки.")
        if self.instance and self.instance.candidates.exists():
            raise serializers.ValidationError("Заявку нельзя изменить после ответа Еңбек.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return JobApplication.objects.create(
            organization=request.user.organization,
            created_by=request.user,
            organization_snapshot=build_organization_snapshot(request.user.organization),
            **validated_data,
        )
