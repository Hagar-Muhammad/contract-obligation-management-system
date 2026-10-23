"""Search, filtering and pagination: FR-SEARCH-01..04, NFR-PERF-02, Arabic-aware matching (decision D-16)."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.search import normalize
from app.modules.users.models import User
from tests.factories import DEFAULT_PASSWORD, UserFactory

Headers = Callable[..., dict[str, str]]


@pytest.fixture
def admin(auth_headers: Headers) -> dict[str, str]:
    return auth_headers("admin")


def _post(client: TestClient, headers: dict[str, str], url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(url, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def _party(
    client: TestClient, headers: dict[str, str], name: str, kind: str = "organization"
) -> dict[str, Any]:
    return _post(client, headers, "/api/v1/parties", {"party_type": kind, "display_name": name})


def _contract(
    client: TestClient, headers: dict[str, str], number: str, title: str, party: dict[str, Any], **extra: Any
) -> dict[str, Any]:
    return _post(
        client,
        headers,
        "/api/v1/contracts",
        {
            "contract_number": number,
            "title": title,
            "type_code": "lease",
            "start_date": "2026-01-01",
            "parties": [{"party_id": party["id"], "role": "landlord"}],
            **extra,
        },
    )


def _names(client: TestClient, headers: dict[str, str], q: str) -> list[str]:
    response = client.get("/api/v1/parties", headers=headers, params={"q": q})
    assert response.status_code == 200, response.text
    return [p["display_name"] for p in response.json()["items"]]


def _login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- Arabic-aware matching (D-16) ----------------------------------------------------------------------------


@pytest.mark.req("FR-SEARCH-01")
@pytest.mark.parametrize(
    ("stored", "typed"),
    [
        ("مؤسسة الأمل للتجارة", "مؤسسه الامل"),  # ta marbuta and hamza-alef typed plainly
        ("مُحَمَّد عَلِي", "محمد علي"),  # diacritics ignored
        ("إسماعيل للمقاولات", "اسماعيل"),  # alef with hamza below
        ("مستشفى النور", "مستشفي"),  # alef maqsura
        ("NILE Crest", "nile crest"),  # case
    ],
)
def test_TC_SEARCH_01_search_ignores_arabic_letter_forms_diacritics_and_case(
    client: TestClient, admin: dict[str, str], stored: str, typed: str
) -> None:
    _party(client, admin, stored)
    _party(client, admin, "Someone Else")
    assert _names(client, admin, typed) == [stored]


@pytest.mark.req("FR-SEARCH-01")
@pytest.mark.parametrize(
    "value", ["مُحَمَّد", "أحمد إبراهيم", "آمنة", "ٱلقرآن", "مدرسة", "مستشفى", "Café ÉLAN", "ـطـويـل", "abc 123"]
)
def test_sql_and_python_normalisation_agree(db: Session, value: str) -> None:
    assert db.scalar(text("SELECT search_normalize(:v)"), {"v": value}) == normalize(value)


@pytest.mark.req("FR-SEARCH-01", "NFR-SEC-06")
def test_typed_wildcards_are_matched_literally(client: TestClient, admin: dict[str, str]) -> None:
    _party(client, admin, "Discount 50% Ltd")
    _party(client, admin, "Fifty 500 Ltd")
    _party(client, admin, "Under_score Co")
    _party(client, admin, "Underscore Co")

    assert _names(client, admin, "50%") == ["Discount 50% Ltd"]
    assert _names(client, admin, "under_") == ["Under_score Co"]


@pytest.mark.req("FR-SEARCH-01")
def test_TC_SEARCH_01_contract_search_finds_arabic_titles_parties_and_properties(
    client: TestClient, admin: dict[str, str]
) -> None:
    owner = _party(client, admin, "شركة النيل العقارية")
    prop = _post(
        client,
        admin,
        "/api/v1/properties",
        {"code": "MAADI-7", "name": "برج المعادي", "property_type": "office"},
    )
    _contract(client, admin, "AR-1", "عقد إيجار مكتب", owner, property_ids=[prop["id"]])
    _contract(client, admin, "EN-1", "Office lease", _party(client, admin, "Other Owner"))

    def numbers(q: str) -> list[str]:
        response = client.get("/api/v1/contracts", headers=admin, params={"q": q})
        return [c["contract_number"] for c in response.json()["items"]]

    assert numbers("ايجار") == ["AR-1"]  # title, typed without hamza
    assert numbers("النيل العقاريه") == ["AR-1"]  # party name, ta marbuta typed as ha
    assert numbers("المعادى") == ["AR-1"]  # property name, ya typed as alef maqsura
    assert numbers("office") == ["EN-1"]


# --- FR-SEARCH-02 --------------------------------------------------------------------------------------------


@pytest.mark.req("FR-SEARCH-02")
def test_TC_SEARCH_02_contracts_filter_by_one_or_more_statuses(
    client: TestClient, admin: dict[str, str]
) -> None:
    party = _party(client, admin, "Nile")
    _contract(client, admin, "D-1", "Draft one", party)
    active = _contract(client, admin, "A-1", "Active one", party, status_code="active")
    ended = _contract(client, admin, "T-1", "Terminated one", party, status_code="active")
    client.patch(f"/api/v1/contracts/{ended['id']}", headers=admin, json={"status_code": "terminated"})

    def numbers(*codes: str) -> list[str]:
        response = client.get("/api/v1/contracts", headers=admin, params={"status_code": list(codes)})
        assert response.status_code == 200, response.text
        return sorted(c["contract_number"] for c in response.json()["items"])

    assert numbers("terminated") == ["T-1"]
    assert numbers("draft", "active") == ["A-1", "D-1"]
    assert active["status"]["code"] == "active"
    assert client.get("/api/v1/contracts", headers=admin, params={"status_code": "open"}).status_code == 422


# --- FR-SEARCH-04 / NFR-PERF-02 ------------------------------------------------------------------------------


@pytest.mark.req("FR-SEARCH-04", "NFR-PERF-02")
@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/users",
        "/api/v1/audit-logs",
        "/api/v1/parties",
        "/api/v1/properties",
        "/api/v1/contracts",
        "/api/v1/obligations",
    ],
)
def test_TC_SEARCH_04_every_list_is_paginated_with_a_capped_page_size(
    client: TestClient, admin: dict[str, str], url: str
) -> None:
    response = client.get(url, headers=admin)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert (body["page"], body["page_size"]) == (1, 25)
    assert client.get(url, headers=admin, params={"page_size": 101}).status_code == 422  # no full-table reads
    assert client.get(url, headers=admin, params={"page": 0}).status_code == 422


@pytest.mark.req("FR-SEARCH-04", "NFR-PERF-02")
def test_TC_SEARCH_04_pages_and_totals_are_computed_by_the_server(
    client: TestClient, admin: dict[str, str]
) -> None:
    for n in range(7):
        _party(client, admin, f"Party {n:02d}")
    _party(client, admin, "Unrelated")

    third = client.get(
        "/api/v1/parties", headers=admin, params={"q": "party", "page": 3, "page_size": 3}
    ).json()
    assert third["total"] == 7  # filtered on the server, counted before paging
    assert [p["display_name"] for p in third["items"]] == ["Party 06"]
    beyond = client.get(
        "/api/v1/parties", headers=admin, params={"q": "party", "page": 9, "page_size": 3}
    ).json()
    assert (beyond["items"], beyond["total"]) == ([], 7)


# --- top-bar search ------------------------------------------------------------------------------------------


@pytest.mark.req("FR-SEARCH-01")
def test_global_search_groups_results_the_user_can_see(
    client: TestClient, admin: dict[str, str], users: UserFactory
) -> None:
    westgate = _party(client, admin, "Westgate Holdings")
    _post(
        client,
        admin,
        "/api/v1/properties",
        {"code": "WG-1", "name": "Westgate Mall", "property_type": "retail"},
    )
    contract = _contract(client, admin, "WG-2026-1", "Westgate lease", westgate)
    omar = users.create("employee")
    _post(
        client,
        admin,
        "/api/v1/obligations",
        {
            "contract_id": contract["id"],
            "title": "Westgate rent",
            "description": "Rent",
            "responsible_party_id": westgate["id"],
            "responsible_user_id": str(omar.id),
            "due_date": "2030-01-01",
        },
    )
    _post(
        client,
        admin,
        "/api/v1/obligations",
        {
            "contract_id": contract["id"],
            "title": "Westgate insurance",
            "description": "Insurance",
            "responsible_party_id": westgate["id"],
            "due_date": "2030-02-01",
        },
    )

    found = client.get("/api/v1/search", headers=admin, params={"q": "westgate"}).json()
    assert [c["contract_number"] for c in found["contracts"]] == ["WG-2026-1"]
    assert [p["display_name"] for p in found["parties"]] == ["Westgate Holdings"]
    assert [p["code"] for p in found["properties"]] == ["WG-1"]
    assert [o["title"] for o in found["obligations"]] == ["Westgate rent", "Westgate insurance"]
    assert found["obligations"][0] == {
        "id": found["obligations"][0]["id"],
        "title": "Westgate rent",
        "contract_number": "WG-2026-1",
        "due_date": "2030-01-01",
        "effective_status": "pending",
    }

    # An employee sees only their obligation, its contract and the contract's parties; no other property.
    mine = client.get("/api/v1/search", headers=_login(client, omar), params={"q": "westgate"}).json()
    assert [o["title"] for o in mine["obligations"]] == ["Westgate rent"]
    assert [c["contract_number"] for c in mine["contracts"]] == ["WG-2026-1"]
    assert [p["display_name"] for p in mine["parties"]] == ["Westgate Holdings"]
    assert mine["properties"] == []

    assert client.get("/api/v1/search", headers=admin, params={"q": "w"}).status_code == 422
    assert client.get("/api/v1/search", headers=admin, params={"q": "westgate", "limit": 1}).json()[
        "obligations"
    ] == [found["obligations"][0]]
