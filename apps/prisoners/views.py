from django.db.models import Exists, OuterRef, Q
from rest_framework import permissions, viewsets

from apps.accounts.models import User
from apps.core.pagination import RegistryPagination

from .models import Prisoner, Skill
from .serializers import PrisonerSerializer, SkillSerializer


class EnbekOnly(permissions.BasePermission):
    allowed_roles = {
        User.Role.ENBEK_ADMIN,
        User.Role.ENBEK_MANAGER,
        User.Role.ENBEK_EXECUTOR,
    }

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in self.allowed_roles


class SkillViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Skill.objects.filter(is_active=True)


class PrisonerViewSet(viewsets.ModelViewSet):
    serializer_class = PrisonerSerializer
    permission_classes = [EnbekOnly]
    pagination_class = RegistryPagination

    def get_queryset(self):
        from apps.contracts.models import EmploymentContract

        queryset = Prisoner.objects.prefetch_related("skills", "change_history").annotate(
            has_active_contracts=Exists(
                EmploymentContract.objects.filter(
                    prisoner_id=OuterRef("pk"), status=EmploymentContract.Status.ACTIVE
                )
            )
        )
        if skill := self.request.query_params.get("skill"):
            queryset = queryset.filter(skills__id=skill)
        if rating := self.request.query_params.get("rating"):
            queryset = queryset.filter(rating=rating)
        if rating_min := self.request.query_params.get("rating_min"):
            if rating_min.isdigit():
                queryset = queryset.filter(rating__gte=int(rating_min))
        if search := self.request.query_params.get("search"):
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(iin__icontains=search)
                | Q(qualification__icontains=search)
                | Q(pre_prison_experience__icontains=search)
                | Q(skills__name_ru__icontains=search)
                | Q(skills__name_kk__icontains=search)
            )
        if education := self.request.query_params.get("education"):
            queryset = queryset.filter(education__icontains=education)
        if qualification := self.request.query_params.get("qualification"):
            queryset = queryset.filter(qualification__icontains=qualification)
        if health := self.request.query_params.get("health"):
            queryset = queryset.filter(health_status__icontains=health)
        if disability := self.request.query_params.get("disability"):
            queryset = queryset.filter(disability_status=disability)
        if employment := self.request.query_params.get("employment"):
            queryset = queryset.filter(current_employment__icontains=employment)
        if experience_min := self.request.query_params.get("experience_min"):
            if experience_min.isdigit():
                queryset = queryset.filter(total_work_experience_years__gte=int(experience_min))
        if self.request.query_params.get("has_medical_restrictions") == "true":
            queryset = queryset.exclude(medical_restrictions="")
        if self.request.query_params.get("has_disciplinary_restrictions") == "true":
            queryset = queryset.exclude(disciplinary_restrictions="")
        if available := self.request.query_params.get("available"):
            if available in {"true", "false"}:
                queryset = queryset.filter(is_available=available == "true")
        return queryset.distinct().order_by("-rating", "full_name", "id")
