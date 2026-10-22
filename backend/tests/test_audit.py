"""Audit trail: FR-AUD-01 (what is recorded), FR-AUD-02 (what a record holds), FR-AUD-03 (records are protected)."""

import contextlib
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app import cli
from app.core.request_context import REQUEST_ID_HEADER
from app.modules.audit.models import AuditLog
from app.modules.auth import service as auth_service
from app.modules.users.models import User
from app.modules.users.rbac import RoleCode
from tests.factories import DEFAULT_PASSWORD, UserFactory

AUDIT = "/api/v1/audit-logs"
USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
Headers = Callable[..., dict[str, str]]


def _entries(db: Session, action: str, target_id: uuid.UUID | None = None) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.occurred_at)
    if target_id is not None:
        stmt = stmt.where(AuditLog.target_id == target_id)
    return list(db.scalars(stmt))


def _only(db: Session, action: str, target_id: uuid.UUID | None = None) -> AuditLog:
    entries = _entries(db, action, target_id)
    assert len(entries) == 1, f"expected one {action}, found {len(entries)}"
    return entries[0]


def _admin(client: TestClient, users: UserFactory) -> tuple[User, dict[str, str]]:
    admin = users.create("admin")
    token = client.post(LOGIN, json={"email": admin.email, "password": DEFAULT_PASSWORD}).json()[
        "access_token"
    ]
    return admin, {"Authorization": f"Bearer {token}"}


def _create_user(client: TestClient, headers: dict[str, str], **overrides: object) -> dict[str, Any]:
    payload = {
        "email": "jane@example.com",
        "full_name": "Jane Doe",
        "password": "Str0ng-Password",
        "role_codes": ["legal"],
        **overrides,
    }
    response = client.post(USERS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


# --- FR-AUD-01: important actions create audit records -------------------------------------------------------


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_creating_a_user_is_recorded(client: TestClient, users: UserFactory, db: Session) -> None:
    admin, headers = _admin(client, users)
    created = _create_user(client, headers)

    entry = _only(db, "user.created", uuid.UUID(created["id"]))
    assert entry.actor_user_id == admin.id
    assert entry.actor_type == "user"
    assert entry.target_type == "user"
    assert entry.target_label == "Jane Doe"
    assert entry.changes == {
        "email": [None, "jane@example.com"],
        "full_name": [None, "Jane Doe"],
        "preferred_language": [None, "en"],
        "roles": [None, ["legal"]],
    }


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_self_sign_up_is_recorded_with_the_new_user_as_actor(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "full_name": "New Person", "password": "Str0ng-Password"},
    )
    assert response.status_code == 201, response.text
    new_id = uuid.UUID(response.json()["user"]["id"])

    entry = _only(db, "user.registered", new_id)
    assert entry.actor_user_id == new_id
    assert entry.changes is not None
    assert entry.changes["roles"] == [None, ["employee"]]
    assert _only(db, "auth.login", new_id).actor_user_id == new_id


@pytest.mark.req("FR-AUD-01", "FR-AUD-02")
def test_TC_AUD_01_editing_a_user_records_only_what_changed(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    admin, headers = _admin(client, users)
    target = users.create("employee", full_name="Old Name")

    response = client.patch(
        f"{USERS}/{target.id}",
        headers=headers,
        json={"full_name": "New Name", "role_codes": ["legal", "employee"], "preferred_language": "en"},
    )
    assert response.status_code == 200, response.text

    entry = _only(db, "user.updated", target.id)
    assert entry.actor_user_id == admin.id
    assert entry.target_label == "New Name"
    assert entry.changes == {
        "full_name": ["Old Name", "New Name"],
        "roles": [["employee"], ["employee", "legal"]],
    }


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_an_edit_that_changes_nothing_is_not_recorded(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    _, headers = _admin(client, users)
    target = users.create("employee", full_name="Same Name")

    assert (
        client.patch(f"{USERS}/{target.id}", headers=headers, json={"full_name": "Same Name"}).status_code
        == 200
    )
    assert _entries(db, "user.updated", target.id) == []


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_password_reset_is_recorded_without_any_password_data(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    admin, headers = _admin(client, users)
    target = users.create("employee")

    response = client.patch(f"{USERS}/{target.id}", headers=headers, json={"password": "Brand-New-Pass1"})
    assert response.status_code == 200, response.text

    entry = _only(db, "user.password_reset", target.id)
    assert entry.actor_user_id == admin.id
    assert entry.changes is None
    assert _entries(db, "user.updated", target.id) == []


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_deactivation_and_reactivation_are_recorded(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    admin, headers = _admin(client, users)
    target = users.create("employee")

    assert client.post(f"{USERS}/{target.id}/deactivate", headers=headers).status_code == 200
    assert client.post(f"{USERS}/{target.id}/activate", headers=headers).status_code == 200
    assert client.post(f"{USERS}/{target.id}/activate", headers=headers).status_code == 200  # already active

    assert _only(db, "user.deactivated", target.id).changes == {"is_active": [True, False]}
    activated = _only(db, "user.activated", target.id)
    assert activated.changes == {"is_active": [False, True]}
    assert activated.actor_user_id == admin.id


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_rejected_changes_leave_no_audit_record(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    admin, headers = _admin(client, users)

    duplicate = client.post(
        USERS,
        headers=headers,
        json={
            "email": admin.email,
            "full_name": "Dup",
            "password": "Str0ng-Password",
            "role_codes": ["legal"],
        },
    )
    assert duplicate.status_code == 409
    assert (
        client.post(f"{USERS}/{admin.id}/deactivate", headers=headers).status_code == 422
    )  # self-deactivation

    assert _entries(db, "user.created") == []
    assert _entries(db, "user.deactivated") == []


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_sign_in_and_sign_out_are_recorded_but_token_refresh_is_not(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    user = users.create()
    login = client.post(LOGIN, json={"email": user.email, "password": DEFAULT_PASSWORD})
    assert login.status_code == 200
    assert _only(db, "auth.login", user.id).actor_user_id == user.id

    before = db.scalar(select(text("count(*)")).select_from(AuditLog))
    assert client.post(REFRESH).status_code == 200
    assert db.scalar(select(text("count(*)")).select_from(AuditLog)) == before

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.post(LOGOUT, headers=headers).status_code == 204
    assert client.post(LOGOUT, headers=headers).status_code == 204  # already ended: not recorded again
    assert _only(db, "auth.logout", user.id).actor_user_id == user.id


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_failed_sign_in_to_an_existing_account_is_recorded(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    user = users.create()
    inactive = users.create(is_active=False)

    assert client.post(LOGIN, json={"email": user.email, "password": "Wrong-Password-1"}).status_code == 401
    assert client.post(LOGIN, json={"email": inactive.email, "password": DEFAULT_PASSWORD}).status_code == 401
    assert (
        client.post(LOGIN, json={"email": "nobody@example.com", "password": "Whatever-123"}).status_code
        == 401
    )

    for target in (user, inactive):
        entry = _only(db, "auth.login_failed", target.id)
        assert entry.actor_type == "anonymous"
        assert entry.actor_user_id is None
    # An unknown e-mail has no account to attach the record to, and what was typed is not stored.
    assert len(_entries(db, "auth.login_failed")) == 2


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_stolen_refresh_token_response_is_recorded_as_a_system_action(
    client: TestClient, users: UserFactory, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth_service, "REUSE_GRACE_PERIOD", timedelta(0))
    user = users.create()
    client.post(LOGIN, json={"email": user.email, "password": DEFAULT_PASSWORD})
    stolen = client.cookies.get("coms_refresh")
    assert stolen
    client.post(REFRESH)

    client.cookies.clear()
    client.cookies.set("coms_refresh", stolen, path="/api/v1/auth")
    assert client.post(REFRESH).status_code == 401

    entry = _only(db, "auth.refresh_token_reused", user.id)
    assert entry.actor_type == "system"
    assert entry.actor_user_id is None


@pytest.mark.req("FR-AUD-01")
def test_TC_AUD_01_create_admin_command_is_recorded_as_a_system_action(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "SessionLocal", lambda: contextlib.nullcontext(db))
    monkeypatch.setenv("COMS_ADMIN_PASSWORD", "First-Admin-Pass1")
    assert cli.main(["create-admin", "--email", "root@example.com", "--name", "Root"]) == 0

    root = db.scalar(select(User).where(User.email == "root@example.com"))
    assert root is not None
    entry = _only(db, "user.created", root.id)
    assert entry.actor_type == "system"
    assert entry.actor_user_id is None


# --- FR-AUD-02: records hold actor, action, target, timestamp and changes; authorized read access --------------


@pytest.mark.req("FR-AUD-02")
def test_TC_AUD_02_record_carries_timestamp_request_id_and_ip(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    _, headers = _admin(client, users)
    response = client.post(
        USERS,
        headers={**headers, REQUEST_ID_HEADER: "req-create-jane"},
        json={
            "email": "jane@example.com",
            "full_name": "Jane",
            "password": "Str0ng-Password",
            "role_codes": ["legal"],
        },
    )
    assert response.headers[REQUEST_ID_HEADER] == "req-create-jane"

    entry = _only(db, "user.created")
    assert entry.occurred_at is not None
    assert entry.request_id == "req-create-jane"
    assert entry.ip_address == "testclient"


@pytest.mark.req("FR-AUD-02")
def test_TC_AUD_02_admin_lists_audit_records_newest_first(client: TestClient, users: UserFactory) -> None:
    admin, headers = _admin(client, users)
    created = _create_user(client, headers)
    client.post(f"{USERS}/{created['id']}/deactivate", headers=headers)

    response = client.get(AUDIT, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["action"] for item in body["items"]] == ["user.deactivated", "user.created", "auth.login"]
    assert body["total"] == 3

    newest = body["items"][0]
    assert newest["actor"] == {"id": str(admin.id), "full_name": admin.full_name, "email": admin.email}
    assert newest["actor_type"] == "user"
    assert newest["target_type"] == "user"
    assert newest["target_id"] == created["id"]
    assert newest["target_label"] == "Jane Doe"
    assert newest["changes"] == {"is_active": [True, False]}
    assert newest["occurred_at"]
    assert newest["request_id"]


@pytest.mark.req("FR-AUD-02", "FR-SEARCH-04")
def test_TC_AUD_02_audit_list_is_paginated(client: TestClient, users: UserFactory) -> None:
    admin, headers = _admin(client, users)
    for n in range(3):
        _create_user(client, headers, email=f"p{n}@example.com", full_name=f"Paged {n}")

    # Newest first: Paged 2, Paged 1 | Paged 0, the admin's sign-in.
    page = client.get(AUDIT, headers=headers, params={"page": 2, "page_size": 2}).json()
    assert page["total"] == 4
    assert [item["target_label"] for item in page["items"]] == ["Paged 0", admin.full_name]


@pytest.mark.req("FR-AUD-02")
def test_TC_AUD_02_audit_list_filters(client: TestClient, users: UserFactory, db: Session) -> None:
    admin, headers = _admin(client, users)
    jane = _create_user(client, headers)
    omar = _create_user(client, headers, email="omar@example.com", full_name="Omar Khaled")
    client.post(f"{USERS}/{omar['id']}/deactivate", headers=headers)

    def actions(**params: str) -> list[str]:
        response = client.get(AUDIT, headers=headers, params=params)
        assert response.status_code == 200, response.text
        return [item["action"] for item in response.json()["items"]]

    assert actions(action="user.created") == ["user.created", "user.created"]
    assert actions(target_id=omar["id"]) == ["user.deactivated", "user.created"]
    assert actions(target_type="user", q="omar") == ["user.deactivated", "user.created"]
    assert actions(q=admin.email) == ["user.deactivated", "user.created", "user.created", "auth.login"]
    assert actions(actor_id=str(uuid.uuid4())) == []

    jane_created = _only(db, "user.created", uuid.UUID(jane["id"]))
    after_jane = jane_created.occurred_at + timedelta(microseconds=1)
    assert actions(occurred_to=jane_created.occurred_at.isoformat()) == ["auth.login"]
    assert actions(occurred_from=after_jane.isoformat()) == ["user.deactivated", "user.created"]

    assert client.get(AUDIT, headers=headers, params={"action": "not.an.action"}).status_code == 422


# --- FR-AUD-03: records cannot be altered or deleted ---------------------------------------------------------


@pytest.mark.req("FR-AUD-03", "NFR-SEC-02")
@pytest.mark.parametrize("role", [r for r in RoleCode if r != RoleCode.ADMIN])
def test_TC_AUD_03_only_authorized_users_can_read_the_audit_log(
    client: TestClient, auth_headers: Headers, role: RoleCode
) -> None:
    assert client.get(AUDIT, headers=auth_headers(role)).status_code == 403


@pytest.mark.req("FR-AUD-03")
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_TC_AUD_03_api_offers_no_way_to_change_audit_records(
    client: TestClient, users: UserFactory, db: Session, method: str
) -> None:
    _, headers = _admin(client, users)
    entry = _only(db, "auth.login")

    assert client.request(method, AUDIT, headers=headers, json={}).status_code == 405
    assert client.request(method, f"{AUDIT}/{entry.id}", headers=headers, json={}).status_code == 404


@pytest.mark.req("FR-AUD-03")
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_logs SET action = 'user.created'",
        "DELETE FROM audit_logs",
        "TRUNCATE audit_logs",
    ],
)
def test_TC_AUD_03_database_rejects_changes_to_audit_records(
    client: TestClient, users: UserFactory, db: Session, statement: str
) -> None:
    _admin(client, users)
    entry = _only(db, "auth.login")

    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.execute(text(statement))

    db.expire_all()
    assert _only(db, "auth.login").action == entry.action


@pytest.mark.req("FR-AUD-03")
def test_TC_AUD_03_orm_cannot_delete_audit_records_either(
    client: TestClient, users: UserFactory, db: Session
) -> None:
    _admin(client, users)
    entry = _only(db, "auth.login")

    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.delete(entry)
        db.flush()
