import contextlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import cli


@pytest.mark.req("FR-USER-01")
def test_create_admin_command_creates_a_working_administrator(
    db: Session, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "SessionLocal", lambda: contextlib.nullcontext(db))
    monkeypatch.setenv("COMS_ADMIN_PASSWORD", "First-Admin-Pass1")

    assert cli.main(["create-admin", "--email", "Root@Example.com", "--name", "Root"]) == 0
    assert cli.main(["create-admin", "--email", "root@example.com", "--name", "Again"]) == 1  # already exists

    login = client.post(
        "/api/v1/auth/login", json={"email": "root@example.com", "password": "First-Admin-Pass1"}
    )
    assert login.status_code == 200
    assert login.json()["user"]["roles"] == ["admin"]


def test_create_admin_rejects_a_weak_password(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "SessionLocal", lambda: contextlib.nullcontext(db))
    monkeypatch.setenv("COMS_ADMIN_PASSWORD", "short")

    assert cli.main(["create-admin", "--email", "root@example.com", "--name", "Root"]) == 1


def test_export_openapi_writes_the_document(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"

    assert cli.main(["export-openapi", str(target)]) == 0
    assert "/api/v1/auth/login" in json.loads(target.read_text(encoding="utf-8"))["paths"]
