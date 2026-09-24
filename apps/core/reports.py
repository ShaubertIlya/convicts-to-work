from datetime import date

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.models import User
from apps.contracts.models import EmploymentContract
from apps.organizations.models import Organization
from apps.prisoners.models import Prisoner


class EnbekLeadership(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated
            and user.role in {User.Role.ENBEK_MANAGER, User.Role.ENBEK_ADMIN}
            and user.organization_id is not None
            and user.organization.kind == Organization.Kind.ENBEK
        )


class ReportDateSerializer(serializers.Serializer):
    as_of = serializers.DateField(required=False, default=timezone.localdate)


def breakdown(queryset, field):
    rows = queryset.order_by().values(field).annotate(count=Count("id")).order_by("-count", field)
    return [{"label": row[field] or "Не указано", "count": row["count"]} for row in rows]


def percentage(numerator: int, denominator: int) -> float | None:
    return round(numerator * 100 / denominator, 1) if denominator else None


@api_view(["GET"])
@permission_classes([EnbekLeadership])
def employment_report(request):
    query = ReportDateSerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    as_of: date = query.validated_data["as_of"]

    # Отсутствующие даты срока не исключают карточку из текущего реестра.
    population = Prisoner.objects.filter(
        Q(sentence_start__isnull=True) | Q(sentence_start__lte=as_of),
        Q(sentence_end__isnull=True) | Q(sentence_end__gte=as_of),
    )
    employed_ids = (
        EmploymentContract.objects.filter(
            prisoner_id__in=population.values("id"),
            starts_on__lte=as_of,
            ends_on__gte=as_of,
        )
        .annotate(
            signed_parties=Count(
                "signatures__party",
                filter=Q(signatures__signed_at__date__lte=as_of),
                distinct=True,
            )
        )
        .filter(signed_parties=3)
        .values("prisoner_id")
        .distinct()
    )

    total = population.count()
    employed = population.filter(id__in=employed_ids).count()
    capable = population.filter(work_capacity=Prisoner.WorkCapacity.CAPABLE)
    capable_total = capable.count()
    capable_employed = capable.filter(id__in=employed_ids).count()

    return Response({
        "as_of": as_of.isoformat(),
        "population_total": total,
        "employed_total": employed,
        "employment_rate_total": percentage(employed, total),
        "work_capable_total": capable_total,
        "work_capable_employed": capable_employed,
        "employment_rate_capable": percentage(capable_employed, capable_total),
        "work_capacity_unknown": population.filter(
            work_capacity=Prisoner.WorkCapacity.UNKNOWN
        ).count(),
        "education": breakdown(population, "education"),
        "qualification": breakdown(population, "qualification"),
        "penitentiary_education": breakdown(population, "penitentiary_education"),
    })
