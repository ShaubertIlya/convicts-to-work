from django.db import connection, models
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from apps.prisoners.models import Prisoner, Skill


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok", "time": timezone.now().isoformat()})


@api_view(["GET"])
@permission_classes([AllowAny])
def public_stats(request):
    skills = (
        Skill.objects.filter(prisoners__is_available=True)
        .values("id", "name_ru", "name_kk")
        .annotate(count=models.Count("prisoners", distinct=True))
        .order_by("name_ru")
    )
    return JsonResponse(
        {
            "total_available": Prisoner.objects.filter(is_available=True).count(),
            "by_skill": list(skills),
        }
    )
