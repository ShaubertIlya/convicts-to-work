from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = (
            "id",
            "recipient",
            "title_ru",
            "title_kk",
            "message_ru",
            "message_kk",
            "related_type",
            "related_id",
            "read_at",
            "created_at",
            "updated_at",
        )
