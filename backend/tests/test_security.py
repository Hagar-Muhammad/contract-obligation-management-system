"""Transport and configuration hardening: NFR-SEC-04 (HTTPS in production)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import DEV_JWT_SECRET, Settings, get_settings
from app.core.db import get_db
from app.main import create_app
from tests.factories import DEFAULT_PASSWORD, UserFactory

PRODUCTION_SECRET = "p" * 48


@pytest.fixture
def production_client(db: Session) -> Iterator[TestClient]:
    settings = Settings(app_env="production", jwt_secret=PRODUCTION_SECRET)
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app, base_url="https://testserver", raise_server_exceptions=False) as client:
        yield client


@pytest.mark.req("NFR-SEC-04")
def test_production_sends_hsts_and_secure_cookies(
    production_client: TestClient, users: UserFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Token signing reads the cached settings; align it with the production instance for this test.
    monkeypatch.setattr(get_settings(), "jwt_secret", PRODUCTION_SECRET)
    user = users.create()

    response = production_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200, response.text
    assert response.headers["strict-transport-security"].startswith("max-age=")
    assert "secure" in response.headers["set-cookie"].lower()


@pytest.mark.req("NFR-SEC-04")
def test_development_does_not_send_hsts(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert "strict-transport-security" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.req("NFR-SEC-04", "NFR-SEC-03")
@pytest.mark.parametrize("secret", [None, "too-short"])
def test_production_refuses_to_start_with_a_weak_jwt_secret(secret: str | None) -> None:
    jwt_secret = secret or DEV_JWT_SECRET
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret=jwt_secret)
    Settings(app_env="development", jwt_secret=jwt_secret)  # local development keeps working
