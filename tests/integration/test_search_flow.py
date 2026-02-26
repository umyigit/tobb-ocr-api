from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
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
                yayin_tarihi="01/01/2020",
                pdf_url="https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=old",
            ),
            GazetteRecord(
                mudurluk="ISTANBUL",
                sicil_no="123456",
                unvan="ACME A.S.",
                yayin_tarihi="15/06/2024",
                pdf_url="https://www.ticaretsicil.gov.tr/view/hizlierisim/pdf_goster.php?Guid=new",
            ),
        ]

        with (
            patch(
                "app.services.search_client.SearchClient.search", return_value=mock_search_results
            ),
            patch(
                "app.services.auth_client.AuthClient.ensure_authenticated", new_callable=AsyncMock
            ),
            patch(
                "app.services.gazette_client.GazetteClient.search",
                return_value=mock_gazette_results,
            ),
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
            # Newest first (2024 before 2020)
            assert "Guid=new" in data["results"][0]["pdf_urls"][0]
            assert "Guid=old" in data["results"][0]["pdf_urls"][1]

    def test_search_not_found(self):
        with patch("app.services.search_client.SearchClient.search") as mock_search:
            mock_search.side_effect = NotFoundError(message="bulunamadi")

            resp = self.client.post("/api/v1/search", json={"trade_name": "NONEXISTENT"})
            assert resp.status_code == 404
            data = resp.json()
            assert data["error_code"] == "NOT_FOUND"
