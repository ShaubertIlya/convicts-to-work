from rest_framework import serializers

from .models import Bank, OkedCode, Organization
from .validators import is_valid_kz_iik


class OkedCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OkedCode
        fields = ("id", "code", "name_ru", "name_kk")


class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = ("id", "bic", "bank_code", "name_ru", "name_kk")


class OrganizationSerializer(serializers.ModelSerializer):
    bank_name = serializers.CharField(source="bank.name_ru", read_only=True)
    bik = serializers.CharField(source="bank.bic", read_only=True)
    oked_name_ru = serializers.SerializerMethodField()
    oked_name_kk = serializers.SerializerMethodField()
    users_count = serializers.IntegerField(read_only=True)
    applications_count = serializers.IntegerField(read_only=True)
    contracts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ("id", "kind", "created_at", "updated_at")

    def get_oked_name_ru(self, obj):
        code = OkedCode.objects.filter(code=obj.oked_code).only("name_ru").first()
        return code.name_ru if code else ""

    def get_oked_name_kk(self, obj):
        code = OkedCode.objects.filter(code=obj.oked_code).only("name_kk").first()
        return code.name_kk if code else ""

    def validate(self, attrs):
        same = attrs.get(
            "actual_address_same", getattr(self.instance, "actual_address_same", False)
        )
        actual = attrs.get("actual_address", getattr(self.instance, "actual_address", ""))
        if not same and not actual:
            raise serializers.ValidationError(
                {"actual_address": "Укажите фактический адрес или отметьте совпадение адресов."}
            )
        if same and "legal_address" in attrs:
            attrs["actual_address"] = attrs["legal_address"]

        bank = attrs.get("bank", getattr(self.instance, "bank", None))
        kbe = attrs.get("kbe", getattr(self.instance, "kbe", ""))
        iik = attrs.get("iik", getattr(self.instance, "iik", ""))
        if self.instance and self.instance.kind == Organization.Kind.BUSINESS:
            errors = {}
            if not bank:
                errors["bank"] = "Выберите банк из справочника."
            elif not bank.is_active:
                errors["bank"] = "Выбранный банк неактивен."
            if not kbe:
                errors["kbe"] = "Укажите КБЕ."
            if not iik:
                errors["iik"] = "Укажите ИИК."
            elif not is_valid_kz_iik(iik):
                errors["iik"] = "Контрольная сумма ИИК некорректна."
            elif bank and iik[4:7] != bank.bank_code:
                errors["iik"] = "Код банка в ИИК не соответствует выбранному банку."
            if errors:
                raise serializers.ValidationError(errors)
        return attrs

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user.role == request.user.Role.BUSINESS_ADMIN:
            editable = {
                "bank",
                "kbe",
                "iik",
                "director_full_name",
                "director_iin",
                "director_position",
                "director_email",
                "director_phone",
            }
            forbidden = set(validated_data) - editable
            if forbidden:
                raise serializers.ValidationError(
                    {field: "Это поле недоступно для редактирования." for field in forbidden}
                )
        return super().update(instance, validated_data)
