from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


class TestOpenAPISchema:
    def setup_method(self):
        app = create_app()
        self.ctx = TestClient(app)
        self.client = self.ctx.__enter__()

    def teardown_method(self):
        self.ctx.__exit__(None, None, None)

    def test_openapi_available(self):
        resp = self.client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "TOBB Ticaret Sicil Gazetesi OCR API"
        assert schema["info"]["version"] == "1.0.0"

    def test_health_endpoint_in_schema(self):
        resp = self.client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/v1/health" in paths

    def test_search_endpoint_in_schema(self):
        resp = self.client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/v1/search" in paths
        assert "post" in paths["/api/v1/search"]

    def test_extract_endpoint_in_schema(self):
        resp = self.client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/v1/extract" in paths
        assert "post" in paths["/api/v1/extract"]
