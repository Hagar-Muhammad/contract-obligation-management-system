"""User administration: FR-USER-01..03 and BR-06 for user management."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.modules.users.rbac import RoleCode
from tests.factories import DEFAULT_PASSWORD, UserFactory

USERS = "/api/v1/users"
Headers = Callable[..., dict[str, str]]


def _new_user(**overrides: object) -> dict[str, object]:
    return {
        "email": "jane@example.com",
        "full_name": "Jane Doe",
        "password": "Str0ng-Password",
        "role_codes": ["legal"],
        **overrides,
    }


@pytest.mark.req("FR-USER-01")
def test_TC_USER_01_admin_creates_user_with_required_role(client: TestClient, auth_headers: Headers) -> None:
    response = client.post(USERS, headers=auth_headers("admin"), json=_new_user(preferred_language="ar"))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "jane@example.com"
    assert body["role_codes"] == ["legal"]
    assert body["preferred_language"] == "ar"
    assert body["is_active"] is True
    assert response.headers["location"] == f"/api/v1/users/{body['id']}"

    login = client.post(
        "/api/v1/auth/login", json={"email": "jane@example.com", "password": "Str0ng-Password"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["roles"] == ["legal"]


@pytest.mark.req("FR-USER-01", "NFR-UX-02")
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"role_codes": []}, "body.role_codes"),
        ({"role_codes": ["superuser"]}, "body.role_codes.0"),
        ({"email": "not-an-email"}, "body.email"),
        ({"password": "short"}, "body.password"),
        ({"full_name": ""}, "body.full_name"),
        ({"unexpected": "field"}, "body.unexpected"),
    ],
)
def test_TC_USER_01_invalid_user_data_is_rejected_per_field(
    client: TestClient, auth_headers: Headers, overrides: dict[str, object], field: str
) -> None:
    response = client.post(USERS, headers=auth_headers("admin"), json=_new_user(**overrides))

    assert response.status_code == 422
    assert field in {d["field"] for d in response.json()["error"]["details"]}


@pytest.mark.req("FR-USER-01")
def test_TC_USER_01_email_must_be_unique_ignoring_case(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    users.create(email="jane@example.com")

    response = client.post(USERS, headers=auth_headers("admin"), json=_new_user(email="JANE@example.com"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


@pytest.mark.req("FR-USER-02")
def test_TC_USER_02_role_change_affects_access_decisions(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    admin = auth_headers("admin")
    employee = users.create("employee")
    employee_token = client.post(
        "/api/v1/auth/login", json={"email": employee.email, "password": DEFAULT_PASSWORD}
    ).json()["access_token"]
    employee_headers = {"Authorization": f"Bearer {employee_token}"}
    assert client.get(USERS, headers=employee_headers).status_code == 403

    response = client.patch(f"{USERS}/{employee.id}", headers=admin, json={"role_codes": ["admin"]})

    assert response.status_code == 200, response.text
    assert response.json()["role_codes"] == ["admin"]
    # Same token, new permissions: access is decided from current roles on every request.
    assert client.get(USERS, headers=employee_headers).status_code == 200


@pytest.mark.req("FR-USER-02")
def test_TC_USER_02_admin_updates_user_information(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    user = users.create()

    response = client.patch(
        f"{USERS}/{user.id}",
        headers=auth_headers("admin"),
        json={"full_name": "Renamed", "email": "Renamed@Example.com", "preferred_language": "ar"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["full_name"], body["email"], body["preferred_language"]) == (
        "Renamed",
        "renamed@example.com",
        "ar",
    )


@pytest.mark.req("FR-USER-02")
def test_TC_USER_02_password_reset_ends_existing_sessions(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    user = users.create()
    old_token = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    ).json()["access_token"]

    response = client.patch(
        f"{USERS}/{user.id}", headers=auth_headers("admin"), json={"password": "Brand-New-Pass1"}
    )

    assert response.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    new_login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "Brand-New-Pass1"})
    assert new_login.status_code == 200


@pytest.mark.req("FR-USER-02")
def test_admin_cannot_remove_own_admin_role(client: TestClient, users: UserFactory) -> None:
    admin = users.create("admin")
    token = client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": DEFAULT_PASSWORD}
    ).json()["access_token"]

    response = client.patch(
        f"{USERS}/{admin.id}", headers={"Authorization": f"Bearer {token}"}, json={"role_codes": ["legal"]}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "business_rule_violation"


@pytest.mark.req("FR-USER-03")
def test_TC_USER_03_deactivated_user_cannot_authenticate(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    user = users.create()
    token = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    ).json()["access_token"]

    response = client.post(f"{USERS}/{user.id}/deactivate", headers=auth_headers("admin"))

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    # Existing session stops working immediately, and a new login is refused.
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})
    assert login.status_code == 401
    assert login.json()["error"]["message"] == "Invalid email or password."


@pytest.mark.req("FR-USER-03")
def test_TC_USER_03_reactivated_user_can_log_in_again(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    user = users.create(is_active=False)

    response = client.post(f"{USERS}/{user.id}/activate", headers=auth_headers("admin"))

    assert response.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})
    assert login.status_code == 200


@pytest.mark.req("FR-USER-03")
def test_admin_cannot_deactivate_self(client: TestClient, users: UserFactory) -> None:
    admin = users.create("admin")
    token = client.post(
        "/api/v1/auth/login", json={"email": admin.email, "password": DEFAULT_PASSWORD}
    ).json()["access_token"]

    response = client.post(f"{USERS}/{admin.id}/deactivate", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 422


@pytest.mark.req("BR-06", "FR-AUTH-03")
@pytest.mark.parametrize("role", [r for r in RoleCode if r != RoleCode.ADMIN])
def test_TC_BR_06_only_administrators_manage_users(
    client: TestClient, auth_headers: Headers, users: UserFactory, role: RoleCode
) -> None:
    headers = auth_headers(role)
    target = users.create()

    assert client.get(USERS, headers=headers).status_code == 403
    assert client.post(USERS, headers=headers, json=_new_user()).status_code == 403
    assert client.patch(f"{USERS}/{target.id}", headers=headers, json={"full_name": "x"}).status_code == 403
    assert client.post(f"{USERS}/{target.id}/deactivate", headers=headers).status_code == 403
    assert client.get("/api/v1/roles", headers=headers).status_code == 403


def test_list_users_is_paginated_and_searchable(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    admin = auth_headers("admin")
    for i in range(3):
        users.create(full_name=f"Searchable Person {i}")

    page = client.get(USERS, headers=admin, params={"q": "searchable", "page_size": 2})

    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 3
    assert body["page"] == 1 and body["page_size"] == 2
    assert len(body["items"]) == 2
    assert client.get(USERS, headers=admin, params={"page_size": 101}).status_code == 422


def test_get_unknown_user_returns_404(client: TestClient, auth_headers: Headers) -> None:
    response = client.get(f"{USERS}/00000000-0000-0000-0000-000000000000", headers=auth_headers("admin"))
    assert response.status_code == 404
