from __future__ import annotations

import io
import time

import httpx
import pytesseract
from PIL import Image

from app.config import Settings
from app.core.exceptions import CaptchaError
from app.core.logging import get_logger
from app.utils.image_processing import preprocess_captcha

logger = get_logger(__name__)

# Different captcha endpoints for login vs search
CAPTCHA_ENDPOINTS = {
    "login": "/captcha/captcha.php",
    "search": "/assets/captcha/captcha.php",
}


class CaptchaHandler:
    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def solve(self, context: str = "search") -> str:
        """Fetch and solve a CAPTCHA image with Tesseract OCR.

        Tries up to CAPTCHA_MAX_ATTEMPTS times, raising CaptchaError if all fail.
        """
        endpoint = CAPTCHA_ENDPOINTS.get(context, CAPTCHA_ENDPOINTS["search"])
        max_attempts = self._settings.CAPTCHA_MAX_ATTEMPTS

        for attempt in range(1, max_attempts + 1):
            try:
                text = await self._fetch_and_ocr(endpoint)
                if text:
                    logger.info(
                        "captcha_solved", context=context, attempt=attempt, length=len(text)
                    )
                    return text
                logger.warning("captcha_empty", context=context, attempt=attempt)
            except Exception:
                logger.warning(
                    "captcha_attempt_failed", context=context, attempt=attempt, exc_info=True
                )

        raise CaptchaError(
            message=f"Captcha {max_attempts} denemede cozulemedi",
            detail=f"context={context}",
        )

    async def _fetch_and_ocr(self, endpoint: str) -> str:
        """Fetch a CAPTCHA image and attempt OCR. Returns cleaned text."""
        image_bytes = await self._fetch_captcha_image(endpoint)
        image = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_captcha(image)

        raw = pytesseract.image_to_string(
            processed,
            config="--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        )
        return self._clean_text(raw)

    async def _fetch_captcha_image(self, endpoint: str) -> bytes:
        """Fetch a raw CAPTCHA image from TOBB."""
        url = f"{self._settings.TOBB_BASE_URL}{endpoint}?{int(time.time() * 1000)}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = "".join(c for c in text.strip() if c.isalnum())
        return cleaned[:4]
