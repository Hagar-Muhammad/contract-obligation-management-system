"""Property register and Property Manager assignments (SRS 4.6; groundwork for FR-PROP-01/02), BR-06, data scope."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.users.models import User
from app.modules.users.rbac import RoleCode
from tests.factories import DEFAULT_PASSWORD, UserFactory

PROPERTIES = "/api/v1/properties"
ASSIGNABLE = f"{PROPERTIES}/assignable-managers"
Headers = Callable[..., dict[str, str]]


def _property(**overrides: object) -> dict[str, object]:
    return {
        "code": "wm-g14",
        "name": "Westgate Mall · Unit G-14",
        "property_type": "retail",
        "city": "Cairo",
        "country": "Egypt",
        "area_sqm": 148,
        **overrides,
    }


def _create(client: TestClient, headers: dict[str, str], payload: dict[str, object]) -> dict[str, Any]:
    response = client.post(PROPERTIES, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def _login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.req("FR-PROP-01")
def test_TC_PROP_01_contract_manager_registers_a_property_with_its_managers(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    youssef = users.create("property_manager", full_name="Youssef Ramadan")
    response = client.post(
        PROPERTIES, headers=auth_headers("contract_manager"), json=_property(manager_ids=[str(youssef.id)])
    )

    assert response.status_code == 201, response.text
    prop = response.json()
    assert response.headers["location"] == f"{PROPERTIES}/{prop['id']}"
    assert prop["code"] == "WM-G14"  # stored upper-cased
    assert prop["property_type"] == "retail"
    assert prop["area_sqm"] == "148.00"
    assert prop["managers"] == [
        {"id": str(youssef.id), "full_name": "Youssef Ramadan", "email": youssef.email}
    ]


@pytest.mark.req("FR-PROP-01", "NFR-UX-02")
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"code": ""}, "body.code"),
        ({"code": "WM#14"}, "body.code"),
        ({"name": " "}, "body.name"),
        ({"property_type": "castle"}, "body.property_type"),
        ({"area_sqm": 0}, "body.area_sqm"),
        ({"area_sqm": "12.345"}, "body.area_sqm"),
        ({"unexpected": 1}, "body.unexpected"),
    ],
)
def test_TC_PROP_01_invalid_property_data_is_rejected_per_field(
    client: TestClient, auth_headers: Headers, overrides: dict[str, object], field: str
) -> None:
    response = client.post(PROPERTIES, headers=auth_headers("admin"), json=_property(**overrides))

    assert response.status_code == 422
    assert field in {d["field"] for d in response.json()["error"]["details"]}


@pytest.mark.req("FR-PROP-01")
def test_TC_PROP_01_property_codes_are_unique_regardless_of_case(
    client: TestClient, auth_headers: Headers
) -> None:
    headers = auth_headers("admin")
    _create(client, headers, _property())

    response = client.post(PROPERTIES, headers=headers, json=_property(code="WM-g14", name="Other"))
    assert response.status_code == 409
    assert response.json()["error"]["details"][0]["field"] == "body.code"


@pytest.mark.req("FR-PROP-01")
def test_TC_PROP_01_only_active_property_managers_can_be_assigned(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    headers = auth_headers("admin")
    legal = users.create("legal")
    former = users.create("property_manager", is_active=False)

    for user in (legal, former):
        response = client.post(PROPERTIES, headers=headers, json=_property(manager_ids=[str(user.id)]))
        assert response.status_code == 422, response.text
        assert response.json()["error"]["details"][0]["field"] == "body.manager_ids"


@pytest.mark.req("FR-PROP-01")
def test_TC_PROP_01_assignable_managers_lists_active_property_managers(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    noha = users.create("property_manager", full_name="Noha Ahmed")
    users.create("property_manager", "employee", full_name="Youssef Ramadan")
    users.create("property_manager", full_name="Gone Away", is_active=False)
    users.create("legal", full_name="Not A Manager")
    headers = auth_headers("contract_manager")

    all_names = [u["full_name"] for u in client.get(ASSIGNABLE, headers=headers).json()]
    assert all_names == ["Noha Ahmed", "Youssef Ramadan"]
    assert client.get(ASSIGNABLE, headers=headers, params={"q": noha.email}).json()[0]["id"] == str(noha.id)
    assert client.get(ASSIGNABLE, headers=auth_headers("legal")).status_code == 403


@pytest.mark.req("FR-PROP-01")
def test_TC_PROP_01_update_replaces_managers_and_is_audited(
    client: TestClient, auth_headers: Headers, users: UserFactory, db: Session
) -> None:
    headers = auth_headers("admin")
    noha = users.create("property_manager", full_name="Noha Ahmed")
    youssef = users.create("property_manager", full_name="Youssef Ramadan")
    prop = _create(client, headers, _property(manager_ids=[str(noha.id)]))

    response = client.patch(
        f"{PROPERTIES}/{prop['id']}",
        headers=headers,
        json={"manager_ids": [str(youssef.id)], "area_sqm": "150.5", "city": None},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert [m["full_name"] for m in updated["managers"]] == ["Youssef Ramadan"]
    assert updated["area_sqm"] == "150.50"
    assert updated["city"] is None
    assert updated["name"] == prop["name"]

    entries = list(
        db.scalars(select(AuditLog).where(AuditLog.target_id == prop["id"]).order_by(AuditLog.occurred_at))
    )
    assert [e.action for e in entries] == ["property.created", "property.updated"]
    assert entries[0].changes is not None
    assert entries[0].changes["managers"] == [None, ["Noha Ahmed"]]
    assert entries[1].changes == {
        "area_sqm": ["148.00", "150.50"],
        "city": ["Cairo", None],
        "managers": [["Noha Ahmed"], ["Youssef Ramadan"]],
    }
    assert entries[1].target_label == "WM-G14 · Westgate Mall · Unit G-14"


@pytest.mark.req("FR-PROP-01")
def test_TC_PROP_01_required_fields_cannot_be_cleared(client: TestClient, auth_headers: Headers) -> None:
    headers = auth_headers("admin")
    prop = _create(client, headers, _property())

    for field in ("code", "name", "property_type"):
        response = client.patch(f"{PROPERTIES}/{prop['id']}", headers=headers, json={field: None})
        assert response.status_code == 422, field


@pytest.mark.req("FR-PROP-01", "FR-SEARCH-04")
def test_TC_PROP_01_list_is_searchable_and_filterable(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    headers = auth_headers("admin")
    noha = users.create("property_manager")
    _create(client, headers, _property(manager_ids=[str(noha.id)]))
    _create(
        client,
        headers,
        _property(code="NC-B", name="Nile Crest Tower B", property_type="office", city="Giza"),
    )

    def codes(**params: str) -> list[str]:
        response = client.get(PROPERTIES, headers=headers, params=params)
        assert response.status_code == 200, response.text
        return [p["code"] for p in response.json()["items"]]

    assert codes() == ["NC-B", "WM-G14"]  # by name: Nile… before Westgate…
    assert codes(q="giza") == ["NC-B"]
    assert codes(q="wm-g") == ["WM-G14"]
    assert codes(property_type="office") == ["NC-B"]
    assert codes(manager_id=str(noha.id)) == ["WM-G14"]


@pytest.mark.req("BR-06", "NFR-SEC-02")
@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        (RoleCode.ADMIN, True),
        (RoleCode.CONTRACT_MANAGER, True),
        (RoleCode.LEGAL, False),
        (RoleCode.PROPERTY_MANAGER, False),
        (RoleCode.EMPLOYEE, False),
        (RoleCode.MANAGEMENT, False),
    ],
)
def test_TC_BR_06_only_property_managers_permission_creates_and_edits_properties(
    client: TestClient, auth_headers: Headers, role: RoleCode, allowed: bool
) -> None:
    prop = _create(client, auth_headers("admin"), _property())
    headers = auth_headers(role)

    create = client.post(PROPERTIES, headers=headers, json=_property(code="NEW-1"))
    update = client.patch(f"{PROPERTIES}/{prop['id']}", headers=headers, json={"notes": "checked"})
    assert (create.status_code, update.status_code) == ((201, 200) if allowed else (403, 403))


@pytest.mark.req("NFR-SEC-02")
def test_property_manager_sees_only_assigned_properties(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    admin = auth_headers("admin")
    manager = users.create("property_manager")
    mine = _create(client, admin, _property(manager_ids=[str(manager.id)]))
    other = _create(client, admin, _property(code="NC-B", name="Nile Crest Tower B"))

    headers = _login(client, manager)
    assert [p["id"] for p in client.get(PROPERTIES, headers=headers).json()["items"]] == [mine["id"]]
    assert client.get(f"{PROPERTIES}/{mine['id']}", headers=headers).status_code == 200
    assert client.get(f"{PROPERTIES}/{other['id']}", headers=headers).status_code == 404


@pytest.mark.req("NFR-SEC-02")
@pytest.mark.parametrize(("role", "sees_all"), [(RoleCode.MANAGEMENT, True), (RoleCode.EMPLOYEE, False)])
def test_property_register_follows_data_scope(
    client: TestClient, auth_headers: Headers, role: RoleCode, sees_all: bool
) -> None:
    prop = _create(client, auth_headers("admin"), _property())
    headers = auth_headers(role)

    listed = client.get(PROPERTIES, headers=headers).json()["items"]
    fetched = client.get(f"{PROPERTIES}/{prop['id']}", headers=headers)
    assert ([p["id"] for p in listed], fetched.status_code) == (
        ([prop["id"]], 200) if sees_all else ([], 404)
    )
