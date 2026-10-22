"""Authentication: FR-AUTH-01, FR-AUTH-02, FR-AUTH-04, NFR-SEC-01, NFR-SEC-03."""

import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.auth.models import UserSession
from tests.factories import DEFAULT_PASSWORD, UserFactory

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"

PUBLIC_ROUTES = {
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/health/ready"),
    ("POST", LOGIN),
    ("POST", REFRESH),
    ("POST", LOGOUT),
}


def _login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):  # type: ignore[no-untyped-def]
    return client.post(LOGIN, json={"email": email, "password": password})


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.req("FR-AUTH-01")
def test_TC_AUTH_01_valid_credentials_create_an_authenticated_session(
    client: TestClient, users: UserFactory
) -> None:
    user = users.create("contract_manager", email="Manager@Example.com")

    response = _login(client, "manager@example.com")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == get_settings().access_token_ttl_minutes * 60
    assert body["user"]["email"] == user.email
    assert body["user"]["roles"] == ["contract_manager"]
    assert "contract:create" in body["user"]["permissions"]

    cookie = response.headers["set-cookie"].lower()
    assert "coms_refresh=" in cookie and "httponly" in cookie and "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie

    me = client.get(ME, headers=_bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["id"] == str(user.id)


@pytest.mark.req("FR-AUTH-01")
def test_TC_AUTH_01_login_is_case_insensitive_on_email(client: TestClient, users: UserFactory) -> None:
    users.create(email="someone@example.com")
    assert _login(client, "  SOMEONE@example.com ").status_code == 200


@pytest.mark.req("FR-AUTH-01")
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("known@example.com", "wrong-password"),
        ("unknown@example.com", DEFAULT_PASSWORD),
        ("not-an-email", "x"),
    ],
)
def test_TC_AUTH_01_invalid_credentials_are_rejected_without_revealing_why(
    client: TestClient, users: UserFactory, email: str, password: str
) -> None:
    users.create(email="known@example.com")

    response = _login(client, email, password)

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "unauthorized", "message": "Invalid email or password."}}
    assert "set-cookie" not in response.headers


@pytest.mark.req("FR-AUTH-02", "NFR-SEC-01")
def test_TC_AUTH_02_every_non_public_endpoint_rejects_unauthenticated_requests(
    client: TestClient, app: FastAPI
) -> None:
    checked = 0
    for path, operations in app.openapi()["paths"].items():
        concrete = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
        for method in operations:
            if (method.upper(), path) in PUBLIC_ROUTES:
                continue
            response = client.request(method.upper(), concrete)
            assert response.status_code == 401, f"{method.upper()} {path} returned {response.status_code}"
            assert response.headers["www-authenticate"] == "Bearer"
            checked += 1
    assert checked >= 8  # guard against the loop silently checking nothing


@pytest.mark.req("FR-AUTH-02")
def test_TC_AUTH_02_malformed_forged_and_expired_tokens_are_rejected(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    user = users.create()
    session = UserSession(user_id=user.id, expires_at=datetime.now(UTC) + timedelta(days=1))
    db.add(session)
    db.commit()
    now = datetime.now(UTC)
    claims = {"sub": str(user.id), "sid": str(session.id), "type": "access", "iat": now}
    settings = get_settings()

    forged = jwt.encode({**claims, "exp": now + timedelta(minutes=5)}, "some-other-secret-0123456789abcdef")
    expired = jwt.encode({**claims, "exp": now - timedelta(seconds=1)}, settings.jwt_secret)
    valid = jwt.encode({**claims, "exp": now + timedelta(minutes=5)}, settings.jwt_secret)

    for token in ["garbage", forged, expired]:
        assert client.get(ME, headers=_bearer(token)).status_code == 401
    assert client.get(ME, headers=_bearer(valid)).status_code == 200


@pytest.mark.req("FR-AUTH-04")
def test_TC_AUTH_04_logout_invalidates_access_and_refresh_tokens(
    client: TestClient, users: UserFactory
) -> None:
    user = users.create()
    login = _login(client, user.email)
    token = login.json()["access_token"]
    refresh_cookie = client.cookies.get("coms_refresh")
    assert refresh_cookie

    response = client.post(LOGOUT, headers=_bearer(token))

    assert response.status_code == 204
    assert (
        'coms_refresh=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]
    )
    assert client.get(ME, headers=_bearer(token)).status_code == 401
    client.cookies.clear()
    client.cookies.set("coms_refresh", refresh_cookie, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401


@pytest.mark.req("FR-AUTH-04")
def test_TC_AUTH_04_logout_with_only_the_refresh_cookie_ends_the_session(
    client: TestClient, users: UserFactory
) -> None:
    user = users.create()
    token = _login(client, user.email).json()["access_token"]

    assert client.post(LOGOUT).status_code == 204  # no Authorization header, cookie only
    assert client.get(ME, headers=_bearer(token)).status_code == 401


@pytest.mark.req("FR-AUTH-04")
def test_TC_AUTH_04_logout_is_idempotent(client: TestClient) -> None:
    assert client.post(LOGOUT).status_code == 204
    assert client.post(LOGOUT, headers=_bearer("garbage")).status_code == 204


@pytest.mark.req("FR-AUTH-01")
def test_refresh_rotates_the_token_and_issues_a_working_access_token(
    client: TestClient, users: UserFactory
) -> None:
    user = users.create()
    _login(client, user.email)
    first_cookie = client.cookies.get("coms_refresh")

    response = client.post(REFRESH)

    assert response.status_code == 200, response.text
    assert client.cookies.get("coms_refresh") != first_cookie
    assert client.get(ME, headers=_bearer(response.json()["access_token"])).status_code == 200


@pytest.mark.req("FR-AUTH-04", "NFR-SEC-02")
def test_reusing_a_rotated_refresh_token_ends_the_session(client: TestClient, users: UserFactory) -> None:
    user = users.create()
    _login(client, user.email)
    stolen = client.cookies.get("coms_refresh")
    assert stolen
    fresh_access = client.post(REFRESH).json()["access_token"]

    client.cookies.clear()
    client.cookies.set("coms_refresh", stolen, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401

    # The legitimate holder is logged out too: the whole session was revoked.
    assert client.get(ME, headers=_bearer(fresh_access)).status_code == 401


@pytest.mark.req("FR-AUTH-01")
def test_refresh_without_cookie_is_rejected(client: TestClient) -> None:
    assert client.post(REFRESH).status_code == 401


@pytest.mark.req("NFR-SEC-03")
def test_passwords_are_stored_as_argon2_hashes(
    client: TestClient, auth_headers: Callable[..., dict[str, str]], db: Session
) -> None:
    from app.modules.users.models import User

    response = client.post(
        "/api/v1/users",
        headers=auth_headers("admin"),
        json={
            "email": "new@example.com",
            "full_name": "New",
            "password": "Plain-Text-123",
            "role_codes": ["legal"],
        },
    )
    assert response.status_code == 201, response.text

    stored = db.get(User, uuid.UUID(response.json()["id"]))
    assert stored is not None
    assert stored.password_hash.startswith("$argon2id$")
    assert "Plain-Text-123" not in stored.password_hash
    assert "password" not in response.text
