from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        TOBB_BASE_URL="https://www.ticaretsicil.gov.tr",
        TOBB_LOGIN_EMAIL="test@test.com",
        TOBB_LOGIN_PASSWORD="testpass",
        VERIFY_SSL=False,
    )


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    with TestClient(app) as c:
        yield c
