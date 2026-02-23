from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


class TestPayloadValidation:
    def setup_method(self):
        app = create_app()
        self.ctx = TestClient(app)
        self.client = self.ctx.__enter__()

    def teardown_method(self):
        self.ctx.__exit__(None, None, None)

    def test_search_missing_trade_name(self):
        resp = self.client.post("/api/v1/search", json={})
        assert resp.status_code == 422

    def test_search_trade_name_too_short(self):
        resp = self.client.post("/api/v1/search", json={"trade_name": "A"})
        assert resp.status_code == 422

    def test_extract_missing_trade_name(self):
        resp = self.client.post("/api/v1/extract", json={})
        assert resp.status_code == 422

    def test_extract_max_results_too_high(self):
        resp = self.client.post(
            "/api/v1/extract", json={"trade_name": "ACME", "max_results": 100}
        )
        assert resp.status_code == 422

    def test_extract_max_results_too_low(self):
        resp = self.client.post(
            "/api/v1/extract", json={"trade_name": "ACME", "max_results": 0}
        )
        assert resp.status_code == 422

    def test_health_response_shape(self):
        resp = self.client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "tobb-ocr-rest-api"
