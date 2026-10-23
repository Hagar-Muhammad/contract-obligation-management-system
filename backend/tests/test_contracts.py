"""Contracts: FR-CON-01..06, FR-PARTY-03, FR-PROP-01/02, BR-02, BR-03, BR-06, BR-07 and data scope."""

from collections.abc import Callable, Sequence
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.contracts.models import ContractType
from app.modules.users.models import User
from app.modules.users.rbac import RoleCode
from tests.factories import DEFAULT_PASSWORD, UserFactory

CONTRACTS = "/api/v1/contracts"
Headers = Callable[..., dict[str, str]]
TODAY = date.today()


@pytest.fixture
def admin(auth_headers: Headers) -> dict[str, str]:
    return auth_headers("admin")


@pytest.fixture
def nile(client: TestClient, admin: dict[str, str]) -> dict[str, Any]:
    return _post(
        client,
        admin,
        "/api/v1/parties",
        {"party_type": "organization", "display_name": "Nile Crest Properties"},
    )


@pytest.fixture
def bloom(client: TestClient, admin: dict[str, str]) -> dict[str, Any]:
    return _post(
        client, admin, "/api/v1/parties", {"party_type": "organization", "display_name": "Bloom Café LLC"}
    )


def _post(client: TestClient, headers: dict[str, str], url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(url, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def _property(
    client: TestClient, headers: dict[str, str], code: str, managers: Sequence[User] = ()
) -> dict[str, Any]:
    return _post(
        client,
        headers,
        "/api/v1/properties",
        {
            "code": code,
            "name": f"Unit {code}",
            "property_type": "retail",
            "manager_ids": [str(m.id) for m in managers],
        },
    )


def _contract(parties: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    roles = ["landlord", "tenant", "other"]
    return {
        "contract_number": "ct-2026-0142",
        "title": "Retail lease — Unit G-14",
        "type_code": "lease",
        "start_date": "2026-01-01",
        "end_date": "2028-12-31",
        "value_amount": "2400000",
        "currency": "egp",
        "parties": [{"party_id": p["id"], "role": roles[i]} for i, p in enumerate(parties)],
        **overrides,
    }


def _login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _numbers(client: TestClient, headers: dict[str, str], **params: str) -> list[str]:
    response = client.get(CONTRACTS, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return [c["contract_number"] for c in response.json()["items"]]


# --- FR-CON-01 / FR-CON-02 / FR-PARTY-03 / FR-PROP-01: create and store ------------------------------------


@pytest.mark.req("FR-CON-01", "FR-CON-02", "FR-PARTY-03", "FR-PROP-01")
def test_TC_CON_01_contract_manager_creates_a_contract_with_parties_and_property(
    client: TestClient,
    auth_headers: Headers,
    admin: dict[str, str],
    nile: dict[str, Any],
    bloom: dict[str, Any],
) -> None:
    prop = _property(client, admin, "WM-G14")
    response = client.post(
        CONTRACTS,
        headers=auth_headers("contract_manager"),
        json=_contract(
            [nile, bloom], property_ids=[prop["id"]], renewal_date="2028-09-30", description=" Café lease "
        ),
    )

    assert response.status_code == 201, response.text
    contract = response.json()
    assert response.headers["location"] == f"{CONTRACTS}/{contract['id']}"
    assert contract["contract_number"] == "CT-2026-0142"
    assert contract["contract_type"]["code"] == "lease"
    assert contract["status"]["code"] == "draft"  # default initial status
    assert contract["status"]["next_codes"] == ["active", "cancelled"]
    assert contract["value_amount"] == "2400000.00"
    assert contract["currency"] == "EGP"
    assert contract["description"] == "Café lease"
    assert contract["renewal_date"] == "2028-09-30"
    assert [(p["display_name"], p["role"]) for p in contract["parties"]] == [
        ("Nile Crest Properties", "landlord"),
        ("Bloom Café LLC", "tenant"),
    ]
    assert [p["code"] for p in contract["properties"]] == ["WM-G14"]
    assert contract["archived_at"] is None
    assert contract["created_by"]["full_name"]

    fetched = client.get(f"{CONTRACTS}/{contract['id']}", headers=admin)  # FR-CON-02: retrievable accurately
    assert fetched.json() == contract


@pytest.mark.req("FR-CON-01", "NFR-UX-02")
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"contract_number": ""}, "body.contract_number"),
        ({"contract_number": "CT#1"}, "body.contract_number"),
        ({"title": "  "}, "body.title"),
        ({"type_code": "timeshare"}, "body.type_code"),
        ({"status_code": "expired"}, "body.status_code"),
        ({"status_code": "unknown"}, "body.status_code"),
        ({"start_date": "not-a-date"}, "body.start_date"),
        ({"currency": "EURO"}, "body.currency"),
        ({"currency": None}, "body.currency"),
        ({"value_amount": None}, "body.value_amount"),
        ({"value_amount": "-1"}, "body.value_amount"),
        ({"unexpected": 1}, "body.unexpected"),
    ],
)
def test_TC_CON_01_invalid_contract_data_is_rejected_per_field(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any], overrides: dict[str, Any], field: str
) -> None:
    response = client.post(CONTRACTS, headers=admin, json=_contract([nile], **overrides))

    assert response.status_code == 422, response.text
    assert field in {d["field"] for d in response.json()["error"]["details"]}


@pytest.mark.req("FR-CON-01")
def test_TC_CON_01_contract_numbers_are_unique_regardless_of_case(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any]
) -> None:
    _post(client, admin, CONTRACTS, _contract([nile]))

    response = client.post(CONTRACTS, headers=admin, json=_contract([nile], contract_number="CT-2026-0142"))
    assert response.status_code == 409
    assert response.json()["error"]["details"][0]["field"] == "body.contract_number"


@pytest.mark.req("FR-CON-01")
def test_TC_CON_01_defaults_suggest_the_next_contract_number(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any]
) -> None:
    year = TODAY.year
    first = client.get(f"{CONTRACTS}/defaults", headers=admin).json()
    assert first == {"next_number": f"CT-{year}-0001", "default_currency": "EGP", "expiring_soon_days": 60}

    _post(client, admin, CONTRACTS, _contract([nile], contract_number=f"CT-{year}-0041"))
    _post(
        client, admin, CONTRACTS, _contract([nile], contract_number=f"CT-{year}-7-B")
    )  # not a plain sequence
    assert client.get(f"{CONTRACTS}/defaults", headers=admin).json()["next_number"] == f"CT-{year}-0042"


# --- BR-02 / BR-03 -------------------------------------------------------------------------------------------


@pytest.mark.req("BR-02")
def test_TC_BR_02_a_contract_needs_at_least_one_party(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any]
) -> None:
    assert client.post(CONTRACTS, headers=admin, json=_contract([])).status_code == 422
    contract = _post(client, admin, CONTRACTS, _contract([nile]))

    response = client.patch(f"{CONTRACTS}/{contract['id']}", headers=admin, json={"parties": []})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body.parties"


@pytest.mark.req("BR-02", "FR-PARTY-03")
def test_TC_BR_02_parties_must_exist_and_appear_once(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any]
) -> None:
    twice = _contract([nile])
    twice["parties"].append({"party_id": nile["id"], "role": "tenant"})
    unknown = _contract([nile])
    unknown["parties"][0]["party_id"] = "00000000-0000-0000-0000-000000000000"

    for payload in (twice, unknown):
        response = client.post(CONTRACTS, headers=admin, json=payload)
        assert response.status_code == 422, response.text
        assert response.json()["error"]["details"][0]["field"] == "body.parties"


@pytest.mark.req("BR-03")
def test_TC_BR_03_end_date_cannot_be_earlier_than_start_date(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any]
) -> None:
    response = client.post(
        CONTRACTS, headers=admin, json=_contract([nile], start_date="2026-11-01", end_date="2026-10-31")
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "body.end_date", "message": "End date can't be earlier than the start date."}
    ]

    contract = _post(client, admin, CONTRACTS, _contract([nile]))  # 2026-01-01 … 2028-12-31
    moved = client.patch(f"{CONTRACTS}/{contract['id']}", headers=admin, json={"start_date": "2029-01-01"})
    assert moved.status_code == 422
    same_day = client.patch(f"{CONTRACTS}/{contract['id']}", headers=admin, json={"end_date": "2026-01-01"})
    assert same_day.status_code == 200
    open_ended = client.patch(f"{CONTRACTS}/{contract['id']}", headers=admin, json={"end_date": None})
    assert open_ended.json()["end_date"] is None


# --- FR-CON-03 / FR-CON-04 -----------------------------------------------------------------------------------


@pytest.mark.req("FR-CON-04", "FR-PARTY-03", "FR-PROP-01")
def test_TC_CON_04_edit_saves_changes_and_audits_them(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any], bloom: dict[str, Any], db: Session
) -> None:
    contract = _post(client, admin, CONTRACTS, _contract([nile, bloom]))
    prop = _property(client, admin, "WM-G14")

    response = client.patch(
        f"{CONTRACTS}/{contract['id']}",
        headers=admin,
        json={
            "title": "Retail lease — Unit G-14, Westgate Mall",
            "value_amount": "2500000",
            "parties": [
                {"party_id": nile["id"], "role": "landlord"},
                {"party_id": bloom["id"], "role": "licensee"},
            ],
            "property_ids": [prop["id"]],
        },
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["title"] == "Retail lease — Unit G-14, Westgate Mall"
    assert {(p["display_name"], p["role"]) for p in updated["parties"]} == {
        ("Nile Crest Properties", "landlord"),
        ("Bloom Café LLC", "licensee"),
    }
    assert [p["code"] for p in updated["properties"]] == ["WM-G14"]

    entry = db.scalar(
        select(AuditLog).where(AuditLog.action == "contract.updated", AuditLog.target_id == contract["id"])
    )
    assert entry is not None
    assert entry.changes == {
        "title": ["Retail lease — Unit G-14", "Retail lease — Unit G-14, Westgate Mall"],
        "value_amount": ["2400000.00", "2500000.00"],
        "parties": [
            ["Bloom Café LLC (tenant)", "Nile Crest Properties (landlord)"],
            ["Bloom Café LLC (licensee)", "Nile Crest Properties (landlord)"],
        ],
        "properties": [[], ["WM-G14"]],
    }


@pytest.mark.req("FR-CON-04", "FR-CON-06")
def test_TC_CON_04_status_follows_the_allowed_transitions(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any], db: Session
) -> None:
    contract = _post(client, admin, CONTRACTS, _contract([nile]))
    url = f"{CONTRACTS}/{contract['id']}"

    assert (
        client.patch(url, headers=admin, json={"status_code": "expired"}).status_code == 422
    )  # draft → expired
    active = client.patch(url, headers=admin, json={"status_code": "active"})
    assert active.status_code == 200
    assert active.json()["status"]["next_codes"] == ["expired", "terminated"]
    assert client.patch(url, headers=admin, json={"status_code": "draft"}).status_code == 422  # no way back
    assert client.patch(url, headers=admin, json={"status_code": "terminated"}).status_code == 200
    assert client.patch(url, headers=admin, json={"status_code": "active"}).status_code == 422  # ended

    changes = [
        e.changes
        for e in db.scalars(
            select(AuditLog)
            .where(AuditLog.action == "contract.status_changed", AuditLog.target_id == contract["id"])
            .order_by(AuditLog.occurred_at)
        )
    ]
    assert changes == [{"status": ["draft", "active"]}, {"status": ["active", "terminated"]}]


@pytest.mark.req("FR-CON-04")
def test_TC_CON_04_an_edit_that_changes_nothing_is_not_audited(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any], db: Session
) -> None:
    contract = _post(client, admin, CONTRACTS, _contract([nile]))
    same = {"title": contract["title"], "value_amount": "2400000.00", "currency": "EGP"}

    assert client.patch(f"{CONTRACTS}/{contract['id']}", headers=admin, json=same).status_code == 200
    assert db.scalar(select(AuditLog).where(AuditLog.action == "contract.updated")) is None


# --- FR-CON-05 / BR-07 ---------------------------------------------------------------------------------------


@pytest.mark.req("FR-CON-05", "BR-07")
def test_TC_CON_05_archived_contracts_leave_active_lists_until_restored(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any]
) -> None:
    kept = _post(client, admin, CONTRACTS, _contract([nile], contract_number="A-1", status_code="active"))
    gone = _post(client, admin, CONTRACTS, _contract([nile], contract_number="A-2", status_code="active"))

    archived = client.post(f"{CONTRACTS}/{gone['id']}/archive", headers=admin)
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert archived.json()["status"]["code"] == "active"  # archiving keeps the status (D-17)

    assert _numbers(client, admin) == ["A-1"]
    assert _numbers(client, admin, view="active") == ["A-1"]
    assert _numbers(client, admin, view="archived") == ["A-2"]
    assert client.get(f"{CONTRACTS}/{gone['id']}", headers=admin).status_code == 200  # still viewable by id
    assert client.patch(f"{CONTRACTS}/{gone['id']}", headers=admin, json={"title": "x"}).status_code == 422
    assert client.post(f"{CONTRACTS}/{gone['id']}/archive", headers=admin).status_code == 422

    assert client.post(f"{CONTRACTS}/{gone['id']}/restore", headers=admin).status_code == 200
    assert _numbers(client, admin, sort="contract_number") == ["A-1", "A-2"]
    assert kept["archived_at"] is None


@pytest.mark.req("FR-CON-05", "BR-07", "FR-SEARCH-04")
def test_TC_CON_05_list_tabs_and_counts(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any]
) -> None:
    def make(number: str, status_code: str = "active", end: date | None = None) -> dict[str, Any]:
        return _post(
            client,
            admin,
            CONTRACTS,
            _contract(
                [nile],
                contract_number=number,
                status_code=status_code,
                start_date="2025-01-01",
                end_date=end.isoformat() if end else None,
            ),
        )

    make("SOON", end=TODAY + timedelta(days=10))
    make("LATER", end=TODAY + timedelta(days=400))
    make("OPEN")
    make("DRAFT", status_code="draft")
    ended = make("ENDED")
    client.patch(f"{CONTRACTS}/{ended['id']}", headers=admin, json={"status_code": "expired"})
    old = make("OLD")
    client.post(f"{CONTRACTS}/{old['id']}/archive", headers=admin)

    assert _numbers(client, admin, view="active") == ["SOON", "LATER", "OPEN"]  # end date, soonest first
    assert _numbers(client, admin, view="expiring") == ["SOON"]
    assert _numbers(client, admin, view="draft") == ["DRAFT"]
    assert _numbers(client, admin, view="ended") == ["ENDED"]
    assert _numbers(client, admin, view="archived") == ["OLD"]
    assert client.get(f"{CONTRACTS}/counts", headers=admin).json() == {
        "active": 3,
        "draft": 1,
        "expiring": 1,
        "ended": 1,
        "archived": 1,
    }


# --- FR-CON-06 -----------------------------------------------------------------------------------------------


@pytest.mark.req("FR-CON-06")
def test_TC_CON_06_types_and_statuses_are_controlled_lists(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any], db: Session
) -> None:
    types = client.get("/api/v1/contract-types", headers=admin).json()
    assert [t["code"] for t in types] == [
        "lease",
        "sale_purchase",
        "service_maintenance",
        "construction",
        "consulting",
        "marketing",
        "partnership",
        "nda",
        "license",
        "other",
    ]
    assert types[0] == {"code": "lease", "name_en": "Lease", "name_ar": "إيجار"}
    statuses = client.get("/api/v1/contract-statuses", headers=admin).json()
    assert [(s["code"], s["next_codes"]) for s in statuses] == [
        ("draft", ["active", "cancelled"]),
        ("active", ["expired", "terminated"]),
        ("expired", []),
        ("terminated", []),
        ("cancelled", []),
    ]

    # A type the business retires can no longer be chosen.
    db.execute(update(ContractType).where(ContractType.code == "nda").values(is_active=False))
    response = client.post(CONTRACTS, headers=admin, json=_contract([nile], type_code="nda"))
    assert response.status_code == 422
    assert "nda" not in [t["code"] for t in client.get("/api/v1/contract-types", headers=admin).json()]


# --- search, filters, FR-PROP-02 -----------------------------------------------------------------------------


@pytest.mark.req("FR-SEARCH-01", "FR-SEARCH-02", "FR-PROP-02", "FR-PARTY-03")
def test_contract_list_search_and_filters(
    client: TestClient, admin: dict[str, str], nile: dict[str, Any], bloom: dict[str, Any]
) -> None:
    prop = _property(client, admin, "WM-G14")
    _post(
        client, admin, CONTRACTS, _contract([nile, bloom], contract_number="L-1", property_ids=[prop["id"]])
    )
    _post(
        client,
        admin,
        CONTRACTS,
        _contract(
            [nile],
            contract_number="S-1",
            title="HVAC service",
            type_code="service_maintenance",
            start_date="2029-01-01",
            end_date=None,
        ),
    )

    assert _numbers(client, admin, q="bloom") == ["L-1"]  # party name
    assert _numbers(client, admin, q="wm-g14") == ["L-1"]  # property code
    assert _numbers(client, admin, q="hvac") == ["S-1"]  # title
    assert _numbers(client, admin, type_code="service_maintenance") == ["S-1"]
    assert _numbers(client, admin, party_id=bloom["id"]) == ["L-1"]
    assert _numbers(client, admin, property_id=prop["id"]) == ["L-1"]  # FR-PROP-02: a property's contracts
    assert _numbers(client, admin, term_from="2029-06-01") == ["S-1"]  # L-1 ended in 2028
    assert _numbers(client, admin, term_to="2027-01-01") == ["L-1"]  # S-1 starts in 2029
    assert _numbers(client, admin, sort="-start_date") == ["S-1", "L-1"]


# --- activity ------------------------------------------------------------------------------------------------


@pytest.mark.req("FR-AUD-02", "FR-CON-03")
def test_contract_activity_is_visible_to_contract_viewers_without_technical_details(
    client: TestClient, admin: dict[str, str], auth_headers: Headers, nile: dict[str, Any]
) -> None:
    contract = _post(client, admin, CONTRACTS, _contract([nile]))
    client.patch(f"{CONTRACTS}/{contract['id']}", headers=admin, json={"status_code": "active"})

    response = client.get(f"{CONTRACTS}/{contract['id']}/activity", headers=auth_headers("management"))
    assert response.status_code == 200, response.text
    activity = response.json()
    assert [a["action"] for a in activity] == ["contract.status_changed", "contract.created"]
    assert activity[0]["changes"] == {"status": ["draft", "active"]}
    assert "ip_address" not in activity[0] and "request_id" not in activity[0]


# --- BR-06 and data scope ------------------------------------------------------------------------------------


@pytest.mark.req("BR-06", "NFR-SEC-02")
@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        (RoleCode.ADMIN, True),
        (RoleCode.CONTRACT_MANAGER, True),
        (RoleCode.LEGAL, True),
        (RoleCode.EMPLOYEE, False),
        (RoleCode.MANAGEMENT, False),
    ],
)
def test_TC_BR_06_create_edit_and_archive_need_their_permissions(
    client: TestClient,
    auth_headers: Headers,
    admin: dict[str, str],
    nile: dict[str, Any],
    role: RoleCode,
    allowed: bool,
) -> None:
    existing = _post(client, admin, CONTRACTS, _contract([nile], contract_number="E-1"))
    headers = auth_headers(role)

    create = client.post(CONTRACTS, headers=headers, json=_contract([nile], contract_number="N-1"))
    edit = client.patch(f"{CONTRACTS}/{existing['id']}", headers=headers, json={"title": "Edited"})
    archive = client.post(f"{CONTRACTS}/{existing['id']}/archive", headers=headers)
    expected = (201, 200, 200) if allowed else (403, 403, 403)
    assert (create.status_code, edit.status_code, archive.status_code) == expected


@pytest.mark.req("NFR-SEC-02", "FR-PROP-01")
def test_property_manager_works_only_on_contracts_of_their_properties(
    client: TestClient, users: UserFactory, admin: dict[str, str], nile: dict[str, Any]
) -> None:
    manager = users.create("property_manager")
    mine = _property(client, admin, "MINE", [manager])
    other = _property(client, admin, "OTHER")
    on_mine = _post(
        client, admin, CONTRACTS, _contract([nile], contract_number="M-1", property_ids=[mine["id"]])
    )
    on_other = _post(
        client, admin, CONTRACTS, _contract([nile], contract_number="O-1", property_ids=[other["id"]])
    )
    _post(client, admin, CONTRACTS, _contract([nile], contract_number="NONE"))
    headers = _login(client, manager)

    assert _numbers(client, headers) == ["M-1"]
    assert client.get(f"{CONTRACTS}/{on_other['id']}", headers=headers).status_code == 404
    assert (
        client.patch(f"{CONTRACTS}/{on_other['id']}", headers=headers, json={"title": "x"}).status_code == 404
    )
    assert client.get(f"{CONTRACTS}/counts", headers=headers).json()["draft"] == 1

    # Their new contracts must be on one of their properties, and only properties they can see.
    without = client.post(CONTRACTS, headers=headers, json=_contract([nile], contract_number="P-1"))
    assert without.status_code == 422
    assert without.json()["error"]["details"][0]["field"] == "body.property_ids"
    foreign = client.post(
        CONTRACTS, headers=headers, json=_contract([nile], contract_number="P-2", property_ids=[other["id"]])
    )
    assert foreign.status_code == 422
    created = client.post(
        CONTRACTS, headers=headers, json=_contract([nile], contract_number="P-3", property_ids=[mine["id"]])
    )
    assert created.status_code == 201
    # …and they cannot move a contract off their properties.
    moved = client.patch(f"{CONTRACTS}/{on_mine['id']}", headers=headers, json={"property_ids": []})
    assert moved.status_code == 422


@pytest.mark.req("NFR-SEC-02")
@pytest.mark.parametrize(("role", "sees"), [(RoleCode.MANAGEMENT, True), (RoleCode.EMPLOYEE, False)])
def test_contracts_follow_data_scope(
    client: TestClient,
    auth_headers: Headers,
    admin: dict[str, str],
    nile: dict[str, Any],
    role: RoleCode,
    sees: bool,
) -> None:
    contract = _post(client, admin, CONTRACTS, _contract([nile]))
    headers = auth_headers(role)

    listed = _numbers(client, headers)
    fetched = client.get(f"{CONTRACTS}/{contract['id']}", headers=headers)
    activity = client.get(f"{CONTRACTS}/{contract['id']}/activity", headers=headers)
    if sees:
        assert (listed, fetched.status_code, activity.status_code) == (["CT-2026-0142"], 200, 200)
    else:
        # Employees see contracts through their obligations (module 6); until then, none.
        assert (listed, fetched.status_code, activity.status_code) == ([], 404, 404)
