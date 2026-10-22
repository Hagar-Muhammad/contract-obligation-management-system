"""Self sign-up: change request CR-01 (docs/decisions.md D-20)."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.factories import UserFactory

REGISTER = "/api/v1/auth/register"


def _signup(**overrides: object) -> dict[str, object]:
    return {
        "email": "New.Person@Example.com",
        "full_name": "New Person",
        "password": "Fresh-Pass-123",
        **overrides,
    }


@pytest.mark.req("CR-01")
def test_TC_CR_01_visitor_creates_an_account_and_is_signed_in(client: TestClient) -> None:
    response = client.post(REGISTER, json=_signup(preferred_language="ar"))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["email"] == "new.person@example.com"
    assert body["user"]["roles"] == ["employee"]
    assert body["user"]["preferred_language"] == "ar"
    assert "httponly" in response.headers["set-cookie"].lower()

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    # The same credentials work for a normal login afterwards.
    login = client.post(
        "/api/v1/auth/login", json={"email": "new.person@example.com", "password": "Fresh-Pass-123"}
    )
    assert login.status_code == 200


@pytest.mark.req("CR-01", "BR-06")
def test_TC_CR_01_self_registered_users_get_only_the_default_role(client: TestClient) -> None:
    token = client.post(REGISTER, json=_signup()).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/users", headers=headers).status_code == 403


@pytest.mark.req("CR-01")
def test_TC_CR_01_the_role_cannot_be_chosen_by_the_visitor(client: TestClient) -> None:
    response = client.post(REGISTER, json=_signup(role_codes=["admin"]))

    assert response.status_code == 422
    assert "body.role_codes" in {d["field"] for d in response.json()["error"]["details"]}


@pytest.mark.req("CR-01")
def test_TC_CR_01_an_existing_email_cannot_register_again(client: TestClient, users: UserFactory) -> None:
    users.create(email="taken@example.com")

    response = client.post(REGISTER, json=_signup(email="TAKEN@example.com"))

    assert response.status_code == 409


@pytest.mark.req("CR-01", "NFR-UX-02")
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"password": "short"}, "body.password"),
        ({"email": "nope"}, "body.email"),
        ({"full_name": ""}, "body.full_name"),
    ],
)
def test_TC_CR_01_invalid_sign_up_data_is_rejected(
    client: TestClient, overrides: dict[str, object], field: str
) -> None:
    response = client.post(REGISTER, json=_signup(**overrides))

    assert response.status_code == 422
    assert field in {d["field"] for d in response.json()["error"]["details"]}


@pytest.mark.req("CR-01")
def test_TC_CR_01_sign_up_can_be_switched_off(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "self_signup_enabled", False)

    assert client.get("/api/v1/auth/options").json() == {"self_signup_enabled": False}
    response = client.post(REGISTER, json=_signup())
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_options_report_sign_up_enabled_by_default(client: TestClient) -> None:
    assert client.get("/api/v1/auth/options").json() == {"self_signup_enabled": True}
