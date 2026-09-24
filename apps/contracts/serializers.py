from rest_framework import serializers

from apps.organizations.snapshots import build_organization_snapshot

from .models import BiometricSignatureAttempt, ContractSignature, EmploymentContract


class ContractSignatureSerializer(serializers.ModelSerializer):
    signed_by_name = serializers.CharField(source="signed_by.full_name", read_only=True)

    class Meta:
        model = ContractSignature
        fields = ("party", "method", "signed_by_name", "signed_at")


class EmploymentContractSerializer(serializers.ModelSerializer):
    signatures = ContractSignatureSerializer(many=True, read_only=True)
    prisoner_name = serializers.CharField(source="prisoner.full_name", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_details = serializers.SerializerMethodField()

    def get_organization_details(self, obj):
        return obj.organization_snapshot or build_organization_snapshot(obj.organization)

    class Meta:
        model = EmploymentContract
        fields = (
            "id",
            "number",
            "application",
            "candidate",
            "prisoner",
            "prisoner_name",
            "organization",
            "organization_name",
            "organization_details",
            "starts_on",
            "ends_on",
            "status",
            "document",
            "document_hash",
            "document_version",
            "signatures",
            "created_at",
        )
        read_only_fields = fields


class BiometricAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricSignatureAttempt
        fields = ("id", "verification_id", "status", "expires_at", "completed_at")
