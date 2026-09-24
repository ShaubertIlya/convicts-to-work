from django.db.models import Count
from rest_framework import filters, mixins, permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.core.pagination import RegistryPagination
from apps.core.permissions import NonClinicalAuthenticated

from .models import Bank, OkedCode, Organization
from .serializers import BankSerializer, OkedCodeSerializer, OrganizationSerializer


class OkedCodeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OkedCodeSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ["code", "name_ru", "name_kk"]
    queryset = OkedCode.objects.filter(is_active=True)


class BankViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BankSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ["bic", "bank_code", "name_ru", "name_kk"]
    queryset = Bank.objects.filter(is_active=True)


class OrganizationViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrganizationSerializer
    permission_classes = [NonClinicalAuthenticated]
    pagination_class = RegistryPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "bin", "activity_type", "oked_code", "director_full_name"]
    ordering_fields = ["name", "created_at", "staff_count"]
    ordering = ["name"]

    def get_queryset(self):
        user = self.request.user
        queryset = Organization.objects.select_related("bank").annotate(
            users_count=Count("users", distinct=True),
            applications_count=Count("applications", distinct=True),
            contracts_count=Count("contracts", distinct=True),
        )
        if user.role == User.Role.BUSINESS_ADMIN:
            return queryset.filter(id=user.organization_id)
        if user.organization and user.organization.kind == Organization.Kind.ENBEK:
            if kind := self.request.query_params.get("kind"):
                queryset = queryset.filter(kind=kind)
            return queryset
        return queryset.none()

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == User.Role.BUSINESS_ADMIN and serializer.instance.id == user.organization_id:
            serializer.save()
            return
        if user.role == User.Role.ENBEK_ADMIN:
            serializer.save()
            return
        raise PermissionDenied("Изменение организаций доступно администратору Еңбек.")
