from .models import Notification


def notify_users(users, *, title_ru, title_kk, related_type="", related_id=None):
    Notification.objects.bulk_create(
        [
            Notification(
                recipient=user,
                title_ru=title_ru,
                title_kk=title_kk,
                related_type=related_type,
                related_id=related_id,
            )
            for user in users
        ]
    )
