from urllib.parse import quote

import httpx
from django.conf import settings


class BiometryError(RuntimeError):
    pass


class BiometryClient:
    def __init__(self):
        self.base_url = settings.BIOMETRY_BASE_URL.rstrip("/")
        self.public_url = settings.BIOMETRY_PUBLIC_URL.rstrip("/")
        self.timeout = settings.BIOMETRY_TIMEOUT_SECONDS

    def start(self, reference_file, state: str) -> dict:
        signature = reference_file.read(8)
        reference_file.seek(0)
        if signature.startswith(b"\xff\xd8"):
            content_type = "image/jpeg"
        elif signature.startswith(b"\x89PNG\r\n\x1a\n"):
            content_type = "image/png"
        else:
            raise BiometryError("Эталонное фото должно быть в формате JPEG или PNG.")
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/verification/start",
                data={"state": state},
                files={"reference_image": (reference_file.name, reference_file, content_type)},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BiometryError("Не удалось начать биометрическую проверку.") from exc

    def consume(self, verification_id: str) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/verification/{quote(verification_id, safe='')}/consume",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BiometryError("Не удалось подтвердить результат биометрии.") from exc

    def frontend_url(self, verification_id: str) -> str:
        return f"{self.public_url}/biometry/?verification_id={quote(verification_id, safe='')}"
