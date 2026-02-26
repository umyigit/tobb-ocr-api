from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import AuthError
from app.main import create_app
from app.schemas.responses import ExtractResult


@pytest.mark.integration
class TestExtractFlow:
    def setup_method(self):
        self.app = create_app()
        self.ctx = TestClient(self.app)
        self.client = self.ctx.__enter__()

    def teardown_method(self):
        self.ctx.__exit__(None, None, None)

    def test_extract_success(self):
        mock_result = ExtractResult(
            source_pdf_url="https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc",
            raw_text="sample text",
        )

        with patch("app.services.extractor.Extractor.extract_from_url", return_value=mock_result):
            resp = self.client.post(
                "/api/v1/extract",
                json={
                    "pdf_url": "https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc"
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["raw_text"] == "sample text"
            assert data["source_pdf_url"] is not None
            assert data["error"] is None

    def test_extract_with_error(self):
        mock_result = ExtractResult(
            source_pdf_url="https://example.com/pdf",
            error="PDF indirilemedi",
        )

        with patch("app.services.extractor.Extractor.extract_from_url", return_value=mock_result):
            resp = self.client.post(
                "/api/v1/extract",
                json={"pdf_url": "https://example.com/pdf"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["error"] == "PDF indirilemedi"

    def test_extract_auth_error(self):
        with patch("app.services.extractor.Extractor.extract_from_url") as mock_ext:
            mock_ext.side_effect = AuthError(message="Login basarisiz")

            resp = self.client.post(
                "/api/v1/extract",
                json={"pdf_url": "https://example.com/pdf"},
            )
            assert resp.status_code == 401
            data = resp.json()
            assert data["error_code"] == "AUTH_FAILED"
