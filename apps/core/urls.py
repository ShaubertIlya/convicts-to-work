from django.urls import path

from .reports import employment_report
from .views import csrf, health, public_stats

urlpatterns = [
    path("health/", health, name="health"),
    path("csrf/", csrf, name="csrf"),
    path("public/stats/", public_stats, name="public-stats"),
    path("reports/employment/", employment_report, name="employment-report"),
]
