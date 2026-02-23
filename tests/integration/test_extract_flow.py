from __future__ import annotations

import pytest
from unittest.mock import patch

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
        mock_results = [
            ExtractResult(
                trade_name="ACME A.S.",
                registry_city="Istanbul",
                registry_no="123456",
                publication_date="01/01/2024",
                issue_no="10987",
                notice_type="KURULUS",
                source_pdf_url="https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc",
                raw_text="sample text",
                parse_confidence=1.0,
            )
        ]

        with patch("app.services.extractor.Extractor.extract", return_value=mock_results):
            resp = self.client.post("/api/v1/extract", json={"trade_name": "ACME"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["query"] == "ACME"
            assert data["successful"] == 1
            assert data["results"][0]["trade_name"] == "ACME A.S."
            assert data["results"][0]["registry_city"] == "Istanbul"
            assert data["results"][0]["registry_no"] == "123456"
            assert data["results"][0]["notice_type"] == "KURULUS"
            assert data["results"][0]["raw_text"] == "sample text"

    def test_extract_only_trade_name_needed(self):
        """User should only need to provide trade_name."""
        mock_results = [
            ExtractResult(
                trade_name="TEST LTD",
                registry_city="Ankara",
                registry_no="789",
                source_pdf_url="https://example.com/pdf",
                raw_text="some text",
                parse_confidence=0.4,
            )
        ]

        with patch("app.services.extractor.Extractor.extract", return_value=mock_results):
            resp = self.client.post("/api/v1/extract", json={"trade_name": "TEST LTD"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["results"][0]["trade_name"] == "TEST LTD"
            assert data["results"][0]["registry_city"] == "Ankara"

    def test_extract_partial_failure(self):
        mock_results = [
            ExtractResult(
                trade_name="ACME A.S.",
                registry_city="Istanbul",
                registry_no="123",
                source_pdf_url="https://example.com/gazette1.pdf",
                raw_text="some text",
                parse_confidence=0.2,
            ),
            ExtractResult(
                trade_name="ACME A.S.",
                registry_city="Istanbul",
                registry_no="123",
                source_pdf_url="https://example.com/gazette2.pdf",
                error="PDF indirilemedi",
            ),
        ]

        with patch("app.services.extractor.Extractor.extract", return_value=mock_results):
            resp = self.client.post("/api/v1/extract", json={"trade_name": "ACME"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_processed"] == 2
            assert data["successful"] == 1
            assert data["results"][1]["error"] == "PDF indirilemedi"

    def test_extract_auth_error(self):
        with patch("app.services.extractor.Extractor.extract") as mock_ext:
            mock_ext.side_effect = AuthError(message="Login basarisiz")

            resp = self.client.post("/api/v1/extract", json={"trade_name": "ACME"})
            assert resp.status_code == 401
            data = resp.json()
            assert data["error_code"] == "AUTH_FAILED"
