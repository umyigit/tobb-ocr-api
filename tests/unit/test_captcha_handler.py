from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.core.exceptions import CaptchaError
from app.services.captcha_handler import CaptchaHandler


@pytest.fixture
def mock_client():
    client = AsyncMock()
    return client


@pytest.fixture
def handler(mock_client):
    settings = Settings(
        TOBB_BASE_URL="https://www.ticaretsicil.gov.tr",
        CAPTCHA_MAX_ATTEMPTS=3,
    )
    return CaptchaHandler(client=mock_client, settings=settings)


class TestCaptchaHandler:
    def test_clean_text_alnum(self):
        assert CaptchaHandler._clean_text("Ab3D!!") == "Ab3D"

    def test_clean_text_truncate(self):
        assert CaptchaHandler._clean_text("ABCDE") == "ABCD"

    def test_clean_text_whitespace(self):
        assert CaptchaHandler._clean_text("  A1 B2  \n") == "A1B2"

    def test_clean_text_empty(self):
        assert CaptchaHandler._clean_text("!!!") == ""

    @pytest.mark.asyncio
    async def test_solve_raises_after_max_attempts(self, handler, mock_client):
        mock_response = AsyncMock()
        mock_response.content = b"fake-image-bytes"
        mock_response.raise_for_status = lambda: None
        mock_client.get.return_value = mock_response

        with patch("app.services.captcha_handler.preprocess_captcha") as mock_pp:
            mock_pp.side_effect = Exception("bad image")
            with pytest.raises(CaptchaError):
                await handler.solve(context="search")

    @pytest.mark.asyncio
    async def test_solve_success(self, handler, mock_client):
        mock_response = AsyncMock()
        mock_response.content = b"fake-png"
        mock_response.raise_for_status = lambda: None
        mock_client.get.return_value = mock_response

        with (
            patch("app.services.captcha_handler.preprocess_captcha") as mock_pp,
            patch("app.services.captcha_handler.pytesseract") as mock_tess,
        ):
            from PIL import Image
            mock_pp.return_value = Image.new("L", (100, 40))
            mock_tess.image_to_string.return_value = "A1B2"

            with patch("app.services.captcha_handler.Image") as mock_image_mod:
                mock_image_mod.open.return_value = Image.new("L", (100, 40))
                result = await handler.solve(context="search")

        assert result == "A1B2"
