from django.conf import settings
from django.core.files.storage import FileSystemStorage


def prisoner_photo_storage():
    """Keep reference photos on local media even when other files use S3."""
    return FileSystemStorage(
        location=settings.MEDIA_ROOT,
        base_url=f"/{settings.MEDIA_URL.lstrip('/')}",
    )
