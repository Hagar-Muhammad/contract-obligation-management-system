"""Obligations: FR-OBL-01..07, BR-01, BR-04, BR-08, FR-PROP-02, evidence (SRS 7.3), permissions and data scope."""

import contextlib
from collections.abc import Callable, Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import cli
from app.core.storage import LocalStorage, get_storage
from app.modules.audit.models import AuditLog
from app.modules.obligations import service as obligations
from app.modules.obligations.models import Obligation
from app.modules.users.models import User
from tests.factories import DEFAULT_PASSWORD, UserFactory

OBLIGATIONS = "/api/v1/obligations"
Headers = Callable[..., dict[str, str]]
PDF = b"%PDF-1.7\n%%EOF\n"


def _day(offset: int) -> str:
    return (obligations.today() + timedelta(days=offset)).isoformat()


@pytest.fixture(autouse=True)
def storage_dir(app: FastAPI, tmp_path: Path) -> Iterator[Path]:
    app.dependency_overrides[get_storage] = lambda: LocalStorage(tmp_path)
    yield tmp_path


@pytest.fixture
def admin(auth_headers: Headers) -> dict[str, str]:
    return auth_headers("admin")


def _post(client: TestClient, headers: dict[str, str], url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(url, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def _login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def setup(client: TestClient, admin: dict[str, str]) -> dict[str, Any]:
    tenant = _post(
        client, admin, "/api/v1/parties", {"party_type": "organization", "display_name": "Bloom Café LLC"}
    )
    landlord = _post(
        client, admin, "/api/v1/parties", {"party_type": "organization", "display_name": "Nile Crest"}
    )
    outsider = _post(
        client, admin, "/api/v1/parties", {"party_type": "individual", "display_name": "Not In It"}
    )
    prop = _post(
        client,
        admin,
        "/api/v1/properties",
        {"code": "WM-G14", "name": "Unit G-14", "property_type": "retail"},
    )
    contract = _post(
        client,
        admin,
        "/api/v1/contracts",
        {
            "contract_number": "CT-1",
            "title": "Retail lease",
            "type_code": "lease",
            "status_code": "active",
            "start_date": "2026-01-01",
            "parties": [
                {"party_id": landlord["id"], "role": "landlord"},
                {"party_id": tenant["id"], "role": "tenant"},
            ],
            "property_ids": [prop["id"]],
        },
    )
    return {
        "tenant": tenant,
        "landlord": landlord,
        "outsider": outsider,
        "contract": contract,
        "property": prop,
    }


def _obligation(setup: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    return {
        "contract_id": setup["contract"]["id"],
        "title": "Quarterly rent payment",
        "description": "Rent for the quarter, paid in advance.",
        "responsible_party_id": setup["tenant"]["id"],
        "due_date": _day(10),
        "priority": "high",
        **overrides,
    }


def _titles(client: TestClient, headers: dict[str, str], **params: str) -> list[str]:
    response = client.get(OBLIGATIONS, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return [o["title"] for o in response.json()["items"]]


# --- FR-OBL-01 / FR-OBL-02 / FR-OBL-03 / BR-01 --------------------------------------------------------------


@pytest.mark.req("FR-OBL-01", "FR-OBL-02", "FR-OBL-03", "BR-01")
def test_TC_OBL_01_obligation_is_created_on_a_contract_with_its_details(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], users: UserFactory, db: Session
) -> None:
    omar = users.create("employee", full_name="Omar Khaled")
    response = client.post(
        OBLIGATIONS,
        headers=admin,
        json=_obligation(
            setup,
            responsible_user_id=str(omar.id),
            start_date=_day(0),
            penalty_text="2% per week late",
            notes="Pay by bank transfer.",
        ),
    )

    assert response.status_code == 201, response.text
    created = response.json()
    assert response.headers["location"] == f"{OBLIGATIONS}/{created['id']}"
    assert created["contract"] == {
        "id": setup["contract"]["id"],
        "contract_number": "CT-1",
        "title": "Retail lease",
    }
    assert created["responsible_party"]["display_name"] == "Bloom Café LLC"
    assert created["responsible_user"] == {"id": str(omar.id), "full_name": "Omar Khaled"}
    assert created["status"] == created["effective_status"] == "pending"
    assert created["priority"] == "high"
    assert created["penalty_text"] == "2% per week late"
    assert created["recurrence_rule"] is None
    assert client.get(f"{OBLIGATIONS}/{created['id']}", headers=admin).json() == created
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "obligation.created"))
    assert entry is not None and entry.changes is not None
    assert entry.changes["responsible_user"] == [None, "Omar Khaled"]


@pytest.mark.req("FR-OBL-01", "BR-01", "FR-OBL-03", "NFR-UX-02")
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"contract_id": "00000000-0000-0000-0000-000000000000"}, "body.contract_id"),
        ({"contract_id": None}, "body.contract_id"),
        ({"title": " "}, "body.title"),
        ({"description": ""}, "body.description"),
        ({"priority": "urgent"}, "body.priority"),
        ({"status": "completed"}, "body.status"),
        ({"start_date": "2030-01-02", "due_date": "2030-01-01"}, "body.due_date"),
        ({"responsible_user_id": "00000000-0000-0000-0000-000000000000"}, "body.responsible_user_id"),
    ],
)
def test_TC_OBL_01_invalid_obligation_data_is_rejected_per_field(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], overrides: dict[str, Any], field: str
) -> None:
    response = client.post(OBLIGATIONS, headers=admin, json=_obligation(setup, **overrides))
    assert response.status_code == 422, response.text
    assert field in {d["field"] for d in response.json()["error"]["details"]}


@pytest.mark.req("FR-OBL-03")
def test_TC_OBL_03_responsible_party_must_be_a_party_of_the_contract(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any]
) -> None:
    response = client.post(
        OBLIGATIONS, headers=admin, json=_obligation(setup, responsible_party_id=setup["outsider"]["id"])
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body.responsible_party_id"


@pytest.mark.req("FR-OBL-02")
def test_TC_OBL_02_an_ongoing_duty_needs_no_due_date(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any]
) -> None:
    created = _post(
        client, admin, OBLIGATIONS, _obligation(setup, due_date=None, title="Keep insurance in force")
    )
    assert created["due_date"] is None
    assert created["effective_status"] == "pending"


@pytest.mark.req("FR-OBL-01")
def test_TC_OBL_01_archived_contracts_take_no_new_obligations(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any]
) -> None:
    client.post(f"/api/v1/contracts/{setup['contract']['id']}/archive", headers=admin)
    assert client.post(OBLIGATIONS, headers=admin, json=_obligation(setup)).status_code == 422


# --- FR-OBL-04 -----------------------------------------------------------------------------------------------


@pytest.mark.req("FR-OBL-04")
def test_TC_OBL_04_status_changes_are_saved_and_audited_with_a_note(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], db: Session
) -> None:
    created = _post(client, admin, OBLIGATIONS, _obligation(setup))
    url = f"{OBLIGATIONS}/{created['id']}/status"

    started = client.post(url, headers=admin, json={"status": "in_progress", "note": "Invoice sent"})
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "in_progress"
    done = client.post(url, headers=admin, json={"status": "completed"}).json()
    assert done["status"] == "completed" and done["completed_at"]
    reopened = client.post(url, headers=admin, json={"status": "in_progress"}).json()
    assert reopened["completed_at"] is None

    changes = [
        e.changes
        for e in db.scalars(
            select(AuditLog)
            .where(AuditLog.action == "obligation.status_changed")
            .order_by(AuditLog.occurred_at)
        )
    ]
    assert changes == [
        {"status": ["pending", "in_progress"], "note": [None, "Invoice sent"]},
        {"status": ["in_progress", "completed"]},
        {"status": ["completed", "in_progress"]},
    ]
    assert client.post(url, headers=admin, json={"status": "overdue"}).status_code == 422  # set by the system


@pytest.mark.req("FR-OBL-04", "NFR-SEC-02", "BR-06")
def test_TC_OBL_04_employees_update_the_status_of_their_own_obligations_only(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], users: UserFactory
) -> None:
    omar = users.create("employee")
    mine = _post(client, admin, OBLIGATIONS, _obligation(setup, responsible_user_id=str(omar.id)))
    other = _post(client, admin, OBLIGATIONS, _obligation(setup, title="Someone else's"))
    headers = _login(client, omar)

    assert (
        client.post(
            f"{OBLIGATIONS}/{mine['id']}/status", headers=headers, json={"status": "in_progress"}
        ).status_code
        == 200
    )
    assert (
        client.patch(f"{OBLIGATIONS}/{mine['id']}", headers=headers, json={"title": "x"}).status_code == 403
    )
    assert (
        client.post(
            f"{OBLIGATIONS}/{other['id']}/status", headers=headers, json={"status": "completed"}
        ).status_code
        == 404
    )
    # Their obligation also opens its contract to them, but not the other obligations on it.
    assert _titles(client, headers) == ["Quarterly rent payment"]
    assert client.get(f"/api/v1/contracts/{setup['contract']['id']}", headers=headers).status_code == 200


@pytest.mark.req("BR-06", "NFR-SEC-02")
@pytest.mark.parametrize(
    ("role", "create", "update"),
    [("admin", 201, 200), ("contract_manager", 201, 200), ("legal", 201, 200), ("management", 403, 403)],
)
def test_TC_BR_06_obligation_permissions_per_role(
    client: TestClient,
    admin: dict[str, str],
    auth_headers: Headers,
    setup: dict[str, Any],
    role: str,
    create: int,
    update: int,
) -> None:
    existing = _post(client, admin, OBLIGATIONS, _obligation(setup))
    headers = auth_headers(role)

    assert client.post(OBLIGATIONS, headers=headers, json=_obligation(setup)).status_code == create
    assert (
        client.patch(f"{OBLIGATIONS}/{existing['id']}", headers=headers, json={"priority": "low"}).status_code
        == update
    )
    assert (
        client.get(f"{OBLIGATIONS}/{existing['id']}", headers=headers).status_code == 200
    )  # all-records scope


# --- FR-OBL-05 / BR-04 ---------------------------------------------------------------------------------------


@pytest.mark.req("FR-OBL-05", "BR-04")
def test_TC_BR_04_obligations_past_their_due_date_are_overdue_until_completed(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], db: Session
) -> None:
    late = _post(client, admin, OBLIGATIONS, _obligation(setup, title="Late", due_date=_day(-7)))
    _post(client, admin, OBLIGATIONS, _obligation(setup, title="Due today", due_date=_day(0)))
    done = _post(client, admin, OBLIGATIONS, _obligation(setup, title="Done late", due_date=_day(-3)))
    client.post(f"{OBLIGATIONS}/{done['id']}/status", headers=admin, json={"status": "completed"})

    assert late["effective_status"] == "overdue" and late["status"] == "pending"
    assert _titles(client, admin, view="overdue") == ["Late"]

    newly = obligations.mark_overdue(db)  # the daily job
    assert [o.title for o in newly] == ["Late"]
    assert obligations.mark_overdue(db) == []  # reported once
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "obligation.overdue"))
    assert entry is not None and entry.actor_type == "system"

    # Moving the due date into the future clears it, so it can be reported again later.
    moved = client.patch(f"{OBLIGATIONS}/{late['id']}", headers=admin, json={"due_date": _day(5)}).json()
    assert moved["effective_status"] == "pending" and moved["overdue_at"] is None


# --- FR-OBL-06 / BR-08 ---------------------------------------------------------------------------------------


@pytest.mark.req("FR-OBL-06", "BR-08")
@pytest.mark.parametrize(
    ("rule", "due"),
    [
        ("FREQ=DAILY", _day(1)),
        ("not a rule", _day(1)),
        ("FREQ=MONTHLY;COUNT=1", _day(1)),
        ("FREQ=MONTHLY", None),
    ],
)
def test_TC_BR_08_a_recurring_obligation_needs_a_valid_rule_and_a_due_date(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], rule: str, due: str | None
) -> None:
    response = client.post(
        OBLIGATIONS, headers=admin, json=_obligation(setup, recurrence_rule=rule, due_date=due)
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["details"][0]["field"] in {"body.recurrence_rule", "body.due_date"}


@pytest.mark.req("FR-OBL-06")
def test_TC_OBL_06_completing_an_occurrence_creates_the_next_one(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any]
) -> None:
    first_due = date(2030, 1, 25)
    first = _post(
        client,
        admin,
        OBLIGATIONS,
        _obligation(setup, due_date=first_due.isoformat(), recurrence_rule="freq=monthly;interval=3"),
    )
    assert first["recurrence_rule"] == "FREQ=MONTHLY;INTERVAL=3"
    assert first["series_id"] == first["id"]

    client.post(f"{OBLIGATIONS}/{first['id']}/status", headers=admin, json={"status": "completed"})
    series = client.get(OBLIGATIONS, headers=admin, params={"sort": "due_date"}).json()["items"]
    assert [(o["due_date"], o["status"]) for o in series] == [
        ("2030-01-25", "completed"),
        ("2030-04-25", "pending"),
    ]
    assert series[1]["series_id"] == first["id"]
    assert series[1]["responsible_party"] == first["responsible_party"]


@pytest.mark.req("FR-OBL-06")
def test_TC_OBL_06_the_daily_job_creates_the_next_occurrence_once_the_due_date_passes(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], db: Session
) -> None:
    past = obligations.today() - timedelta(days=3)
    _post(
        client,
        admin,
        OBLIGATIONS,
        _obligation(setup, due_date=past.isoformat(), recurrence_rule="FREQ=WEEKLY;COUNT=3"),
    )

    assert obligations.roll_recurrences(db) == 1
    assert obligations.roll_recurrences(db) == 0  # next one is in the future
    dues = sorted(o.due_date for o in db.scalars(select(Obligation)) if o.due_date)
    assert dues == [past, past + timedelta(days=7)]
    assert obligations.roll_recurrences(db, on=past + timedelta(days=30)) == 1  # COUNT=3 ends the series
    assert obligations.roll_recurrences(db, on=past + timedelta(days=60)) == 0


@pytest.mark.req("FR-OBL-05", "FR-OBL-06")
def test_daily_jobs_command(
    client: TestClient,
    admin: dict[str, str],
    setup: dict[str, Any],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _post(client, admin, OBLIGATIONS, _obligation(setup, due_date=_day(-2)))
    monkeypatch.setattr(cli, "SessionLocal", lambda: contextlib.nullcontext(db))

    assert cli.main(["run-daily-jobs"]) == 0
    assert "Marked 1 obligation(s) overdue" in capsys.readouterr().out


# --- FR-OBL-07 / FR-PROP-02 ----------------------------------------------------------------------------------


@pytest.mark.req("FR-OBL-07", "FR-SEARCH-03", "FR-PROP-02")
def test_TC_OBL_07_list_search_filters_sort_and_counts(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], users: UserFactory
) -> None:
    omar = users.create("employee")
    _post(client, admin, OBLIGATIONS, _obligation(setup, title="Rent", priority="high", due_date=_day(3)))
    _post(
        client,
        admin,
        OBLIGATIONS,
        _obligation(
            setup,
            title="Insurance proof",
            priority="critical",
            due_date=_day(20),
            responsible_user_id=str(omar.id),
        ),
    )
    late = _post(
        client,
        admin,
        OBLIGATIONS,
        _obligation(
            setup,
            title="Fit-out report",
            priority="low",
            due_date=_day(-1),
            responsible_party_id=setup["landlord"]["id"],
        ),
    )
    done = _post(client, admin, OBLIGATIONS, _obligation(setup, title="Deposit", due_date=_day(-30)))
    client.post(f"{OBLIGATIONS}/{done['id']}/status", headers=admin, json={"status": "completed"})
    started = _post(
        client, admin, OBLIGATIONS, _obligation(setup, title="Signage", due_date=None, status="in_progress")
    )

    assert _titles(client, admin) == ["Deposit", "Fit-out report", "Rent", "Insurance proof", "Signage"]
    assert _titles(client, admin, view="open") == ["Fit-out report", "Rent", "Insurance proof", "Signage"]
    assert _titles(client, admin, view="due_this_week") == ["Rent"]
    assert _titles(client, admin, view="in_progress") == ["Signage"]
    assert _titles(client, admin, sort="priority", view="open") == [
        "Insurance proof",
        "Rent",
        "Signage",
        "Fit-out report",
    ]
    assert _titles(client, admin, q="insurance") == ["Insurance proof"]
    assert _titles(client, admin, q="nile") == ["Fit-out report"]  # responsible party
    assert _titles(client, admin, q="ct-1") == _titles(client, admin)  # contract number
    assert _titles(client, admin, priority="critical") == ["Insurance proof"]
    assert _titles(client, admin, responsible_user_id=str(omar.id)) == ["Insurance proof"]
    assert _titles(client, admin, party_id=setup["landlord"]["id"]) == ["Fit-out report"]
    assert _titles(client, admin, property_id=setup["property"]["id"], view="open")[0] == "Fit-out report"
    assert _titles(client, admin, due_from=_day(0), due_to=_day(10)) == ["Rent"]
    assert client.get(f"{OBLIGATIONS}/counts", headers=admin).json() == {
        "open": 4,
        "overdue": 1,
        "due_this_week": 1,
        "in_progress": 1,
        "pending": 2,
        "completed": 1,
        "cancelled": 0,
    }
    assert late["effective_status"] == "overdue" and started["status"] == "in_progress"


@pytest.mark.req("FR-OBL-07")
def test_TC_OBL_07_only_mine(
    client: TestClient, setup: dict[str, Any], admin: dict[str, str], users: UserFactory
) -> None:
    manager = users.create("contract_manager")
    _post(client, admin, OBLIGATIONS, _obligation(setup, title="Mine", responsible_user_id=str(manager.id)))
    _post(client, admin, OBLIGATIONS, _obligation(setup, title="Not mine"))
    assert _titles(client, _login(client, manager), mine="true") == ["Mine"]


# --- contract view: summary and activity ---------------------------------------------------------------------


@pytest.mark.req("FR-CON-03", "FR-OBL-05")
def test_contracts_show_their_open_and_overdue_obligations_and_their_activity(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any]
) -> None:
    _post(client, admin, OBLIGATIONS, _obligation(setup, due_date=_day(-1), title="Late"))
    ok = _post(client, admin, OBLIGATIONS, _obligation(setup, title="On time"))
    client.post(f"{OBLIGATIONS}/{ok['id']}/status", headers=admin, json={"status": "in_progress"})
    contract_id = setup["contract"]["id"]

    detail = client.get(f"/api/v1/contracts/{contract_id}", headers=admin).json()
    assert detail["obligations"] == {"open": 2, "overdue": 1}
    listed = client.get("/api/v1/contracts", headers=admin).json()["items"][0]
    assert listed["obligations"] == {"open": 2, "overdue": 1}
    activity = client.get(f"/api/v1/contracts/{contract_id}/activity", headers=admin).json()
    assert [(a["action"], a["target_label"]) for a in activity[:3]] == [
        ("obligation.status_changed", "On time"),
        ("obligation.created", "On time"),
        ("obligation.created", "Late"),
    ]


# --- evidence (SRS 7.3) --------------------------------------------------------------------------------------


@pytest.mark.req("FR-DOC-01", "FR-OBL-04")
def test_evidence_is_attached_to_the_obligation_and_kept_with_the_contract(
    client: TestClient, admin: dict[str, str], setup: dict[str, Any], users: UserFactory, db: Session
) -> None:
    omar = users.create("employee")
    created = _post(client, admin, OBLIGATIONS, _obligation(setup, responsible_user_id=str(omar.id)))
    headers = _login(client, omar)

    response = client.post(
        f"{OBLIGATIONS}/{created['id']}/evidence",
        headers=headers,
        files={"file": ("insurance-certificate.pdf", PDF, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["kind"] == "evidence"
    assert response.json()["obligation_id"] == created["id"]
    listed = client.get(f"{OBLIGATIONS}/{created['id']}/evidence", headers=headers).json()
    assert [d["original_filename"] for d in listed] == ["insurance-certificate.pdf"]
    assert client.get(f"{OBLIGATIONS}/{created['id']}", headers=headers).json()["evidence_count"] == 1
    contract_docs = client.get(f"/api/v1/contracts/{setup['contract']['id']}/documents", headers=admin).json()
    assert [d["kind"] for d in contract_docs] == ["evidence"]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "obligation.evidence_added")) is not None

    # Evidence is only ever attached from its obligation.
    direct = client.post(
        f"/api/v1/contracts/{setup['contract']['id']}/documents",
        headers=admin,
        files={"file": ("x.pdf", PDF, "application/pdf")},
        data={"kind": "evidence"},
    )
    assert direct.status_code == 422


# --- user directory ------------------------------------------------------------------------------------------


@pytest.mark.req("FR-OBL-03")
def test_user_directory_lists_active_users_for_people_who_assign_obligations(
    client: TestClient, auth_headers: Headers, users: UserFactory
) -> None:
    users.create("employee", full_name="Omar Khaled")
    users.create("employee", full_name="Gone Away", is_active=False)

    names = [
        u["full_name"] for u in client.get("/api/v1/users/directory", headers=auth_headers("legal")).json()
    ]
    assert "Omar Khaled" in names and "Gone Away" not in names
    found = client.get("/api/v1/users/directory", headers=auth_headers("legal"), params={"q": "omar"}).json()
    assert [u["full_name"] for u in found] == ["Omar Khaled"]
    assert set(found[0]) == {"id", "full_name", "email"}
    assert client.get("/api/v1/users/directory", headers=auth_headers("management")).status_code == 403
