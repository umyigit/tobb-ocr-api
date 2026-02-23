from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.exceptions import NotFoundError
from app.main import create_app
from app.schemas.responses import GazetteRecord, SearchRecord


@pytest.mark.integration
class TestSearchFlow:
    def setup_method(self):
        self.app = create_app()
        self.ctx = TestClient(self.app)
        self.client = self.ctx.__enter__()

    def teardown_method(self):
        self.ctx.__exit__(None, None, None)

    def test_search_returns_results_with_pdf_urls(self):
        mock_search_results = (
            [
                SearchRecord(
                    title="ACME A.S.",
                    registry_no="123456",
                    tsm="ISTANBUL",
                )
            ],
            1,
        )
        mock_gazette_results = [
            GazetteRecord(
                mudurluk="ISTANBUL",
                sicil_no="123456",
                unvan="ACME A.S.",
                pdf_url="https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=abc",
            ),
            GazetteRecord(
                mudurluk="ISTANBUL",
                sicil_no="123456",
                unvan="ACME A.S.",
                pdf_url="https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=def",
            ),
        ]

        with (
            patch("app.services.search_client.SearchClient.search", return_value=mock_search_results),
            patch("app.services.auth_client.AuthClient.ensure_authenticated", new_callable=AsyncMock),
            patch("app.services.gazette_client.GazetteClient.search", return_value=mock_gazette_results),
        ):
            resp = self.client.post("/api/v1/search", json={"trade_name": "ACME"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["query"] == "ACME"
            assert data["total_results"] == 1
            assert data["results"][0]["title"] == "ACME A.S."
            assert data["results"][0]["registry_no"] == "123456"
            assert data["results"][0]["tsm"] == "ISTANBUL"
            assert len(data["results"][0]["pdf_urls"]) == 2
            assert "pdf_goster.php?Guid=abc" in data["results"][0]["pdf_urls"][0]

    def test_search_not_found(self):
        with patch("app.services.search_client.SearchClient.search") as mock_search:
            mock_search.side_effect = NotFoundError(message="bulunamadi")

            resp = self.client.post("/api/v1/search", json={"trade_name": "NONEXISTENT"})
            assert resp.status_code == 404
            data = resp.json()
            assert data["error_code"] == "NOT_FOUND"
