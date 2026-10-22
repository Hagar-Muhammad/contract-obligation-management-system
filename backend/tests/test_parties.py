"""Party directory: FR-PARTY-01 (create, view, update), FR-PARTY-02 (individuals and organizations), BR-06."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.users.rbac import RoleCode

PARTIES = "/api/v1/parties"
Headers = Callable[..., dict[str, str]]


def _individual(**overrides: object) -> dict[str, object]:
    return {
        "party_type": "individual",
        "display_name": "Hany Fawzy",
        "national_id": "2850 1011 2345 67",
        **overrides,
    }


def _organization(**overrides: object) -> dict[str, object]:
    return {
        "party_type": "organization",
        "display_name": "Nile Crest Properties",
        "registration_no": "41872",
        "tax_no": "300-221-118",
        "email": "Leasing@NileCrest.example.com",
        "phone": "+20 2 2735 0000",
        **overrides,
    }


def _create(client: TestClient, headers: dict[str, str], payload: dict[str, object]) -> dict[str, Any]:
    response = client.post(PARTIES, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


@pytest.mark.req("FR-PARTY-01", "FR-PARTY-02")
def test_TC_PARTY_01_contract_manager_creates_and_views_an_organization(
    client: TestClient, auth_headers: Headers
) -> None:
    headers = auth_headers("contract_manager")
    response = client.post(PARTIES, headers=headers, json=_organization())

    assert response.status_code == 201, response.text
    party = response.json()
    assert response.headers["location"] == f"{PARTIES}/{party['id']}"
    assert party["party_type"] == "organization"
    assert party["display_name"] == "Nile Crest Properties"
    assert party["email"] == "leasing@nilecrest.example.com"
    assert party["tax_no"] == "300-221-118"
    assert party["national_id"] is None

    fetched = client.get(f"{PARTIES}/{party['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == party


@pytest.mark.req("FR-PARTY-02")
def test_TC_PARTY_02_individual_ids_are_stored_normalised(client: TestClient, auth_headers: Headers) -> None:
    party = _create(client, auth_headers("admin"), _individual(passport_no=" a1234 567 ", email="  "))

    assert party["party_type"] == "individual"
    assert party["national_id"] == "28501011234567"
    assert party["passport_no"] == "A1234567"
    assert party["email"] is None  # blank means not given
    assert party["registration_no"] is None


@pytest.mark.req("FR-PARTY-02", "NFR-UX-02")
@pytest.mark.parametrize(
    ("payload", "fields"),
    [
        (_individual(registration_no="123", tax_no="9"), {"body.registration_no", "body.tax_no"}),
        (_organization(national_id="2850101"), {"body.national_id"}),
        (_organization(passport_no="A1"), {"body.passport_no"}),
    ],
)
def test_TC_PARTY_02_identifiers_of_the_other_party_type_are_rejected(
    client: TestClient, auth_headers: Headers, payload: dict[str, object], fields: set[str]
) -> None:
    response = client.post(PARTIES, headers=auth_headers("admin"), json=payload)

    assert response.status_code == 422, response.text
    assert {d["field"] for d in response.json()["error"]["details"]} == fields


@pytest.mark.req("FR-PARTY-02", "NFR-UX-02")
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"party_type": "trust"}, "body.party_type"),
        ({"display_name": "   "}, "body.display_name"),
        ({"email": "not-an-email"}, "body.email"),
        ({"phone": "call me"}, "body.phone"),
        ({"unexpected": "x"}, "body.unexpected"),
    ],
)
def test_TC_PARTY_02_invalid_party_data_is_rejected_per_field(
    client: TestClient, auth_headers: Headers, overrides: dict[str, object], field: str
) -> None:
    response = client.post(PARTIES, headers=auth_headers("admin"), json=_organization(**overrides))

    assert response.status_code == 422
    assert field in {d["field"] for d in response.json()["error"]["details"]}


@pytest.mark.req("FR-PARTY-01")
def test_TC_PARTY_01_the_same_official_number_cannot_be_recorded_twice(
    client: TestClient, auth_headers: Headers
) -> None:
    headers = auth_headers("admin")
    _create(client, headers, _organization())

    response = client.post(
        PARTIES, headers=headers, json=_organization(display_name="Copy Co", registration_no="41 872")
    )
    assert response.status_code == 409
    assert response.json()["error"]["details"] == [
        {"field": "body.registration_no", "message": "Already recorded for Nile Crest Properties."}
    ]


@pytest.mark.req("FR-PARTY-01")
def test_TC_PARTY_01_update_changes_only_the_fields_sent_and_is_audited(
    client: TestClient, auth_headers: Headers, db: Session
) -> None:
    headers = auth_headers("legal")
    party = _create(client, headers, _organization())

    response = client.patch(
        f"{PARTIES}/{party['id']}",
        headers=headers,
        json={"display_name": "Nile Crest Holding", "phone": None},
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["display_name"] == "Nile Crest Holding"
    assert updated["phone"] is None
    assert updated["registration_no"] == "41872"  # not sent, unchanged

    entries = list(
        db.scalars(select(AuditLog).where(AuditLog.target_id == updated["id"]).order_by(AuditLog.occurred_at))
    )
    assert [e.action for e in entries] == ["party.created", "party.updated"]
    assert entries[1].changes == {
        "display_name": ["Nile Crest Properties", "Nile Crest Holding"],
        "phone": ["+20 2 2735 0000", None],
    }
    assert entries[1].target_label == "Nile Crest Holding"


@pytest.mark.req("FR-PARTY-02")
def test_TC_PARTY_02_party_type_cannot_change_and_foreign_ids_cannot_be_added(
    client: TestClient, auth_headers: Headers
) -> None:
    headers = auth_headers("admin")
    party = _create(client, headers, _individual())

    assert (
        client.patch(
            f"{PARTIES}/{party['id']}", headers=headers, json={"party_type": "organization"}
        ).status_code
        == 422
    )
    assert client.patch(f"{PARTIES}/{party['id']}", headers=headers, json={"tax_no": "1"}).status_code == 422
    assert (
        client.patch(f"{PARTIES}/{party['id']}", headers=headers, json={"display_name": None}).status_code
        == 422
    )


@pytest.mark.req("FR-PARTY-01", "FR-SEARCH-04")
def test_TC_PARTY_01_list_is_alphabetical_searchable_and_filterable(
    client: TestClient, auth_headers: Headers
) -> None:
    headers = auth_headers("admin")
    _create(client, headers, _organization())
    _create(client, headers, _individual())
    _create(
        client,
        headers,
        _organization(
            display_name="Al-Safwa Facility Services", registration_no="77", email="info@alsafwa.example.com"
        ),
    )

    def names(**params: str) -> list[str]:
        response = client.get(PARTIES, headers=headers, params=params)
        assert response.status_code == 200, response.text
        return [p["display_name"] for p in response.json()["items"]]

    assert names() == ["Al-Safwa Facility Services", "Hany Fawzy", "Nile Crest Properties"]
    assert names(party_type="individual") == ["Hany Fawzy"]
    assert names(q="nile") == ["Nile Crest Properties"]
    assert names(q="nilecrest.example") == ["Nile Crest Properties"]  # e-mail
    assert names(q="2850 1011 2345 67") == ["Hany Fawzy"]  # exact ID, typed with spaces
    assert names(q="2850") == []  # partial IDs do not match
    page = client.get(PARTIES, headers=headers, params={"page": 2, "page_size": 2}).json()
    assert page["total"] == 3
    assert [p["display_name"] for p in page["items"]] == ["Nile Crest Properties"]


@pytest.mark.req("BR-06", "NFR-SEC-02")
@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        (RoleCode.ADMIN, True),
        (RoleCode.CONTRACT_MANAGER, True),
        (RoleCode.LEGAL, True),
        (RoleCode.PROPERTY_MANAGER, True),
        (RoleCode.EMPLOYEE, False),
        (RoleCode.MANAGEMENT, False),
    ],
)
def test_TC_BR_06_only_party_managers_create_and_edit_parties(
    client: TestClient, auth_headers: Headers, role: RoleCode, allowed: bool
) -> None:
    party = _create(client, auth_headers("admin"), _organization())
    headers = auth_headers(role)

    create = client.post(PARTIES, headers=headers, json=_individual())
    update = client.patch(f"{PARTIES}/{party['id']}", headers=headers, json={"notes": "checked"})
    assert (create.status_code, update.status_code) == ((201, 200) if allowed else (403, 403))


@pytest.mark.req("NFR-SEC-02")
@pytest.mark.parametrize(
    ("role", "sees_directory"),
    [
        (RoleCode.MANAGEMENT, True),  # all records, read-only
        (RoleCode.PROPERTY_MANAGER, True),  # manages parties, so picks them for contracts
        (RoleCode.EMPLOYEE, False),  # only parties of their own work, from module 4 on
    ],
)
def test_party_directory_follows_data_scope(
    client: TestClient, auth_headers: Headers, role: RoleCode, sees_directory: bool
) -> None:
    party = _create(client, auth_headers("admin"), _organization())
    headers = auth_headers(role)

    listed = client.get(PARTIES, headers=headers).json()["items"]
    fetched = client.get(f"{PARTIES}/{party['id']}", headers=headers)
    if sees_directory:
        assert [p["id"] for p in listed] == [party["id"]]
        assert fetched.status_code == 200
    else:
        assert listed == []
        assert fetched.status_code == 404  # not 403: out-of-scope records are not revealed
