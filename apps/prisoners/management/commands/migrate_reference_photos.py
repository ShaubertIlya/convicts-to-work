from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from storages.backends.s3 import S3Storage

from apps.prisoners.models import Prisoner
from apps.prisoners.storage import prisoner_photo_storage


class Command(BaseCommand):
    help = "Копирует фото карточек из прежнего S3-хранилища в локальную media-папку."

    def handle(self, *args, **options):
        if not getattr(settings, "AWS_S3_ENDPOINT_URL", None):
            raise CommandError("Не настроен прежний S3 endpoint для переноса фото.")

        source = S3Storage()
        destination = prisoner_photo_storage()
        copied = skipped = 0
        names = (
            Prisoner.objects.exclude(photo="")
            .order_by("photo")
            .values_list("photo", flat=True)
            .distinct()
        )
        for name in names:
            if not name.startswith("prisoners/reference/"):
                raise CommandError(f"Неожиданный путь фото: {name}")
            if destination.exists(name):
                skipped += 1
                continue
            try:
                with source.open(name, "rb") as image:
                    saved_name = destination.save(name, image)
            except Exception as exc:
                raise CommandError(f"Не удалось перенести {name}: {exc}") from exc
            if saved_name != name:
                raise CommandError(
                    f"Фото {name} сохранено под другим именем {saved_name}; проверьте данные."
                )
            copied += 1

        self.stdout.write(self.style.SUCCESS(f"Фото: перенесено {copied}, уже на месте {skipped}."))
