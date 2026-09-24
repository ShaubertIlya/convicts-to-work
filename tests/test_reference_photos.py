from io import StringIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from PIL import Image

from apps.prisoners.models import Prisoner


def test_prisoner_reference_photo_uses_local_storage():
    storage = Prisoner._meta.get_field("photo").storage
    assert isinstance(storage, FileSystemStorage)
    assert storage.url("prisoners/reference/example.jpg") == (
        "/media/prisoners/reference/example.jpg"
    )


@pytest.mark.django_db
def test_demo_seed_uses_local_photo_and_preserves_replaced_reference(
    tmp_path, settings, monkeypatch
):
    settings.MEDIA_ROOT = tmp_path
    monkeypatch.setattr(
        Prisoner._meta.get_field("photo"),
        "storage",
        FileSystemStorage(location=tmp_path, base_url="/media/"),
    )
    reference = tmp_path / "prisoners/reference/public-portrait-01.jpg"
    reference.parent.mkdir(parents=True)
    Image.new("RGB", (80, 100), "blue").save(reference)

    call_command("seed_demo", stdout=StringIO())
    prisoner = Prisoner.objects.get(iin="900101000001")
    assert prisoner.photo.name == "prisoners/reference/public-portrait-01.jpg"

    prisoner.photo.save("personal-reference.jpg", ContentFile(reference.read_bytes()))
    personal_name = prisoner.photo.name
    call_command("seed_demo", stdout=StringIO())
    prisoner.refresh_from_db()
    assert prisoner.photo.name == personal_name
