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
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/verification/start",
                data={"state": state},
                files={"reference_image": (reference_file.name, reference_file, "image/jpeg")},
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
