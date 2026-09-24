from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title_ru = models.CharField(max_length=255)
    title_kk = models.CharField(max_length=255)
    message_ru = models.TextField(blank=True)
    message_kk = models.TextField(blank=True)
    related_type = models.CharField(max_length=32, blank=True)
    related_id = models.UUIDField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
