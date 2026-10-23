"""Contract documents: FR-DOC-01..05, BR-09, NFR-SEC-05, NFR-SEC-06, BR-06 and data scope."""

import hashlib
import io
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.storage import LocalStorage, get_storage
from app.modules.audit.models import AuditLog
from app.modules.users.models import User
from tests.factories import DEFAULT_PASSWORD, UserFactory

Headers = Callable[..., dict[str, str]]

PDF = b"%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def _docx(*, macros: bool = False) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("word/document.xml", "<w:document/>")
        if macros:
            package.writestr("word/vbaProject.bin", b"\x00")
    return buffer.getvalue()


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


@pytest.fixture
def contract(client: TestClient, admin: dict[str, str]) -> dict[str, Any]:
    party = _post(
        client, admin, "/api/v1/parties", {"party_type": "organization", "display_name": "Nile Crest"}
    )
    return _new_contract(client, admin, party, "CT-1")


def _new_contract(
    client: TestClient,
    headers: dict[str, str],
    party: dict[str, Any],
    number: str,
    property_ids: list[str] = (),  # type: ignore[assignment]
) -> dict[str, Any]:
    return _post(
        client,
        headers,
        "/api/v1/contracts",
        {
            "contract_number": number,
            "title": f"Contract {number}",
            "type_code": "lease",
            "start_date": "2026-01-01",
            "parties": [{"party_id": party["id"], "role": "landlord"}],
            "property_ids": list(property_ids),
        },
    )


def _upload(
    client: TestClient,
    headers: dict[str, str],
    contract_id: str,
    content: bytes = PDF,
    name: str = "Lease_G14_signed.pdf",
    kind: str = "contract",
) -> Any:
    return client.post(
        f"/api/v1/contracts/{contract_id}/documents",
        headers=headers,
        files={"file": (name, content, "application/octet-stream")},
        data={"kind": kind},
    )


def _login(client: TestClient, user: User) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- FR-DOC-01 / FR-DOC-05 -----------------------------------------------------------------------------------


@pytest.mark.req("FR-DOC-01", "FR-DOC-05", "BR-09")
def test_TC_DOC_01_upload_links_the_file_to_its_contract_and_records_metadata(
    client: TestClient, admin: dict[str, str], contract: dict[str, Any], db: Session
) -> None:
    response = _upload(client, admin, contract["id"])

    assert response.status_code == 201, response.text
    document = response.json()
    assert response.headers["location"] == f"/api/v1/documents/{document['id']}"
    assert document["contract_id"] == contract["id"]
    assert document["kind"] == "contract"
    assert document["original_filename"] == "Lease_G14_signed.pdf"
    assert document["file_type"] == "pdf"
    assert document["mime_type"] == "application/pdf"
    assert document["size_bytes"] == len(PDF)
    assert document["uploaded_by"]["full_name"]
    assert document["uploaded_at"]
    assert "storage_key" not in document  # storage location never leaves the server

    listed = client.get(f"/api/v1/contracts/{contract['id']}/documents", headers=admin).json()
    assert [d["id"] for d in listed] == [document["id"]]
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "contract.document_uploaded"))
    assert entry is not None
    assert str(entry.target_id) == contract["id"]
    assert entry.changes == {"document": [None, "Lease_G14_signed.pdf"]}


@pytest.mark.req("FR-DOC-05", "NFR-SEC-06")
@pytest.mark.parametrize(
    ("name", "stored"),
    [
        ("..\\..\\etc\\evil.pdf", "evil.pdf"),
        ("/home/user/../annex.pdf", "annex.pdf"),
        (
            "invoice" + chr(0x202E) + "fdp.pdf",
            "invoicefdp.pdf",
        ),  # right-to-left override: a filename-spoofing trick
        ("عقد_الإيجار.pdf", "عقد_الإيجار.pdf"),
        ("...", "document"),
    ],
)
def test_TC_DOC_05_file_names_are_kept_without_paths_or_control_characters(
    client: TestClient, admin: dict[str, str], contract: dict[str, Any], name: str, stored: str
) -> None:
    response = _upload(client, admin, contract["id"], name=name)
    assert response.status_code == 201, response.text
    assert response.json()["original_filename"] == stored


# --- FR-DOC-02 -----------------------------------------------------------------------------------------------


@pytest.mark.req("FR-DOC-02", "FR-DOC-03")
def test_TC_DOC_02_the_original_is_preserved_byte_for_byte(
    client: TestClient, admin: dict[str, str], contract: dict[str, Any], storage_dir: Path
) -> None:
    document = _upload(
        client, admin, contract["id"], content=_docx(), name="Annex A.docx", kind="annex"
    ).json()

    response = client.get(f"/api/v1/documents/{document['id']}/download", headers=admin)
    assert response.status_code == 200
    assert response.content == _docx()
    assert hashlib.sha256(response.content).hexdigest() == document["sha256"]
    assert [p for p in storage_dir.rglob("*") if p.is_file()]  # kept on disk, under an opaque key
    assert all("Annex" not in p.name for p in storage_dir.rglob("*"))


@pytest.mark.req("FR-DOC-02")
def test_TC_DOC_02_there_is_no_way_to_change_or_delete_an_original(
    client: TestClient, admin: dict[str, str], contract: dict[str, Any]
) -> None:
    document = _upload(client, admin, contract["id"]).json()
    url = f"/api/v1/documents/{document['id']}"

    for method in ("PUT", "PATCH", "DELETE"):
        assert client.request(method, url, headers=admin).status_code == 405
        assert client.request(method, f"{url}/download", headers=admin).status_code == 405


@pytest.mark.req("FR-DOC-02")
def test_TC_DOC_02_storage_refuses_to_overwrite_an_existing_original(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    key = storage.new_key()
    storage.save(key, io.BytesIO(b"first"))

    with pytest.raises(FileExistsError):
        storage.save(key, io.BytesIO(b"second"))
    with storage.open(key) as handle:
        assert handle.read() == b"first"
    with pytest.raises(ValueError):
        storage.open("../outside")


# --- FR-DOC-03 / NFR-SEC-05 ----------------------------------------------------------------------------------


@pytest.mark.req("FR-DOC-03", "NFR-SEC-05")
def test_TC_DOC_03_download_is_an_attachment_that_cannot_run_in_the_browser(
    client: TestClient, admin: dict[str, str], contract: dict[str, Any], db: Session
) -> None:
    document = _upload(client, admin, contract["id"], name="عقد الإيجار.pdf").json()

    response = client.get(f"/api/v1/documents/{document['id']}/download", headers=admin)
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        "attachment; filename=\"document.pdf\"; filename*=UTF-8''%D8%B9%D9%82%D8%AF%20%D8%A7%D9%84%D8%A5%D9%8A%D8%AC%D8%A7%D8%B1.pdf"
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "private, no-store"

    entry = db.scalar(select(AuditLog).where(AuditLog.action == "document.downloaded"))
    assert entry is not None
    assert str(entry.target_id) == document["id"]


@pytest.mark.req("FR-DOC-03", "NFR-SEC-05", "NFR-SEC-02")
def test_TC_DOC_03_documents_follow_the_contract_s_scope(
    client: TestClient, admin: dict[str, str], auth_headers: Headers, users: UserFactory
) -> None:
    party = _post(client, admin, "/api/v1/parties", {"party_type": "organization", "display_name": "Nile"})
    manager = users.create("property_manager")
    mine = _post(
        client,
        admin,
        "/api/v1/properties",
        {"code": "MINE", "name": "Mine", "property_type": "retail", "manager_ids": [str(manager.id)]},
    )
    on_mine = _new_contract(client, admin, party, "M-1", [mine["id"]])
    elsewhere = _new_contract(client, admin, party, "O-1")
    mine_doc = _upload(client, admin, on_mine["id"]).json()
    other_doc = _upload(client, admin, elsewhere["id"]).json()

    pm = _login(client, manager)
    assert client.get(f"/api/v1/documents/{mine_doc['id']}/download", headers=pm).status_code == 200
    assert client.get(f"/api/v1/documents/{other_doc['id']}/download", headers=pm).status_code == 404
    assert client.get(f"/api/v1/documents/{other_doc['id']}", headers=pm).status_code == 404
    assert client.get(f"/api/v1/contracts/{elsewhere['id']}/documents", headers=pm).status_code == 404

    management = auth_headers("management")  # read-only, all records
    assert client.get(f"/api/v1/documents/{other_doc['id']}/download", headers=management).status_code == 200
    employee = auth_headers("employee")  # sees documents of their obligations' contracts (module 6)
    assert client.get(f"/api/v1/documents/{mine_doc['id']}/download", headers=employee).status_code == 404


@pytest.mark.req("BR-06", "FR-DOC-01")
@pytest.mark.parametrize(
    ("role", "expected"),
    [("admin", 201), ("contract_manager", 201), ("legal", 201), ("management", 403), ("employee", 404)],
)
def test_TC_BR_06_upload_needs_the_permission_and_the_contract_in_scope(
    client: TestClient, auth_headers: Headers, contract: dict[str, Any], role: str, expected: int
) -> None:
    # Employees hold document:upload, but only for contracts of their own obligations (none yet): 404.
    assert _upload(client, auth_headers(role), contract["id"]).status_code == expected


# --- FR-DOC-04 / NFR-SEC-06 ----------------------------------------------------------------------------------


@pytest.mark.req("FR-DOC-04", "NFR-SEC-06")
@pytest.mark.parametrize(
    ("content", "name", "file_type"),
    [
        (PDF, "a.pdf", "pdf"),
        (_docx(), "b.docx", "docx"),
        (PNG, "c.png", "png"),
        (JPG, "d.jpeg", "jpg"),
        (PDF, "scan-without-extension", "pdf"),
    ],
)
def test_TC_DOC_04_supported_types_are_recognised_by_content(
    client: TestClient,
    admin: dict[str, str],
    contract: dict[str, Any],
    content: bytes,
    name: str,
    file_type: str,
) -> None:
    response = _upload(client, admin, contract["id"], content=content, name=name)
    assert response.status_code == 201, response.text
    assert response.json()["file_type"] == file_type


@pytest.mark.req("FR-DOC-04", "NFR-SEC-06")
@pytest.mark.parametrize(
    ("content", "name"),
    [
        (b"MZ\x90\x00 an executable", "contract.pdf"),  # a disguised program
        (_docx(macros=True), "contract.docx"),  # macro-enabled Word file
        (b"PK\x03\x04 not really a zip", "contract.docx"),
        (b"plain text", "notes.txt"),
        (b"<html><script>alert(1)</script>", "page.pdf"),
    ],
)
def test_TC_DOC_04_other_files_are_rejected_with_a_clear_error(
    client: TestClient,
    admin: dict[str, str],
    contract: dict[str, Any],
    storage_dir: Path,
    content: bytes,
    name: str,
) -> None:
    response = _upload(client, admin, contract["id"], content=content, name=name)

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"
    assert (
        response.json()["error"]["message"] == "This file type is not supported. Upload PDF, DOCX, PNG, JPG."
    )
    assert not [p for p in storage_dir.rglob("*") if p.is_file()]  # nothing kept


@pytest.mark.req("FR-DOC-04")
def test_TC_DOC_04_size_limit_and_empty_files(
    client: TestClient, admin: dict[str, str], contract: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "upload_max_bytes", 1024)

    too_big = _upload(client, admin, contract["id"], content=PDF + b"x" * 2000)
    assert too_big.status_code == 413
    assert too_big.json()["error"]["code"] == "payload_too_large"
    declared = _upload(client, admin, contract["id"], content=PDF + b"x" * 200_000)  # refused before reading
    assert declared.status_code == 413
    empty = _upload(client, admin, contract["id"], content=b"")
    assert empty.status_code == 422
    assert client.get("/api/v1/documents/limits", headers=admin).json() == {
        "max_bytes": 1024,
        "allowed_types": ["pdf", "docx", "png", "jpg"],
    }


@pytest.mark.req("FR-DOC-04")
def test_TC_DOC_04_allowed_types_follow_the_setting(
    client: TestClient, admin: dict[str, str], contract: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "upload_allowed_types", ["pdf"])

    assert _upload(client, admin, contract["id"], content=PNG, name="photo.png").status_code == 415
    assert _upload(client, admin, contract["id"]).status_code == 201


# --- BR-09 ---------------------------------------------------------------------------------------------------


@pytest.mark.req("BR-09")
def test_TC_BR_09_documents_need_an_existing_open_contract(
    client: TestClient, admin: dict[str, str], contract: dict[str, Any]
) -> None:
    unknown = _upload(client, admin, "00000000-0000-0000-0000-000000000000")
    assert unknown.status_code == 404

    client.post(f"/api/v1/contracts/{contract['id']}/archive", headers=admin)
    archived = _upload(client, admin, contract["id"])
    assert archived.status_code == 422
    assert "Restore the contract" in archived.json()["error"]["message"]


@pytest.mark.req("FR-DOC-04", "NFR-SEC-06")
def test_TC_DOC_04_oversized_bodies_are_refused_before_they_are_read(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "upload_max_bytes", 1024)
    big = b"x" * 200_000

    declared = client.post("/api/v1/auth/login", content=big, headers={"Content-Type": "application/json"})
    assert declared.status_code == 413
    assert declared.json()["error"]["code"] == "payload_too_large"

    def chunks() -> Iterator[bytes]:  # no Content-Length: counted as it arrives
        for _ in range(20):
            yield b"x" * 10_000

    streamed = client.post(
        "/api/v1/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert streamed.status_code == 413
