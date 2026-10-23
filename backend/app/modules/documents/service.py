"""Contract documents (FR-DOC-01..05, BR-09, NFR-SEC-05, NFR-SEC-06; decision D-12).

Access follows the contract: whoever can see a contract (and holds document:view) can see its documents; uploading
needs document:upload and a contract in scope that is not archived.
"""

import hashlib
import tempfile
import unicodedata
import uuid
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import BusinessRuleError, NotFoundError, PayloadTooLargeError, UnsupportedMediaTypeError
from app.core.storage import CHUNK_SIZE, StorageBackend
from app.modules.audit import service as audit
from app.modules.audit.actions import AuditAction, TargetType
from app.modules.auth.dependencies import CurrentUser
from app.modules.contracts import service as contracts_service
from app.modules.contracts.scope import visible_contract_ids
from app.modules.documents.filetypes import MIME_TYPES, FileType, detect
from app.modules.documents.models import ContractDocument
from app.modules.documents.schemas import DocumentKind
from app.modules.obligations.models import Obligation

# Kept in memory up to this size, then spilled to a temporary file.
_SPOOL_BYTES = 1024 * 1024


def _clean_filename(name: str | None) -> str:
    """The name to show and offer on download: no path, no control characters, at most 255 characters."""
    base = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(ch for ch in base if unicodedata.category(ch)[0] != "C").strip(" .")
    if len(cleaned) > 255:
        stem, dot, ext = cleaned.rpartition(".")
        cleaned = f"{stem[: 254 - len(ext)]}.{ext}" if dot and len(ext) <= 10 else cleaned[:255]
    return cleaned or "document"


def _receive(source: BinaryIO, target: BinaryIO, max_bytes: int) -> tuple[int, str]:
    """Copy the upload while counting and hashing it; stop as soon as it is too big (FR-DOC-04)."""
    size, digest = 0, hashlib.sha256()
    while chunk := source.read(CHUNK_SIZE):
        size += len(chunk)
        if size > max_bytes:
            raise PayloadTooLargeError(
                f"The file is larger than the {max_bytes // (1024 * 1024)} MB limit.",
                details=[{"field": "body.file", "message": "File too large."}],
            )
        digest.update(chunk)
        target.write(chunk)
    return size, digest.hexdigest()


def list_documents(db: Session, current: CurrentUser, contract_id: uuid.UUID) -> list[ContractDocument]:
    contract = contracts_service.get_contract(db, current, contract_id)
    stmt = (
        select(ContractDocument)
        .where(ContractDocument.contract_id == contract.id)
        .order_by(ContractDocument.uploaded_at.desc(), ContractDocument.id)
    )
    return list(db.scalars(stmt))


def get_document(db: Session, current: CurrentUser, document_id: uuid.UUID) -> ContractDocument:
    """Documents of contracts outside the user's scope are reported as not found (NFR-SEC-05)."""
    document = db.scalar(
        select(ContractDocument).where(
            ContractDocument.id == document_id,
            ContractDocument.contract_id.in_(visible_contract_ids(current)),
        )
    )
    if document is None:
        raise NotFoundError("Document not found.")
    return document


def upload(
    db: Session,
    storage: StorageBackend,
    current: CurrentUser,
    contract_id: uuid.UUID,
    source: BinaryIO,
    filename: str | None,
    kind: DocumentKind,
    *,
    obligation: Obligation | None = None,
) -> ContractDocument:
    """Validate and keep the original (FR-DOC-01, FR-DOC-02, FR-DOC-04) and record its metadata (FR-DOC-05).

    With `obligation`, the file is evidence for it (SRS 7.3); the caller has checked the obligation is in scope.
    """
    settings = get_settings()
    if (kind == DocumentKind.EVIDENCE) != (obligation is not None):
        raise BusinessRuleError(
            "Evidence is attached from its obligation.",
            details=[{"field": "body.kind", "message": "Choose another document type."}],
        )
    contract = obligation.contract if obligation else contracts_service.get_contract(db, current, contract_id)
    if contract.archived_at is not None:
        raise BusinessRuleError("Archived contracts are read-only. Restore the contract to add documents.")

    with tempfile.SpooledTemporaryFile(max_size=_SPOOL_BYTES) as received:
        size, sha256 = _receive(source, received, settings.upload_max_bytes)  # type: ignore[arg-type]
        if size == 0:
            raise BusinessRuleError(
                "The file is empty.", details=[{"field": "body.file", "message": "Empty file."}]
            )
        file_type = detect(received)  # type: ignore[arg-type]
        allowed = [FileType(t) for t in settings.upload_allowed_types]
        if file_type is None or file_type not in allowed:
            names = ", ".join(t.value.upper() for t in allowed)
            raise UnsupportedMediaTypeError(
                f"This file type is not supported. Upload {names}.",
                details=[{"field": "body.file", "message": f"Allowed: {names}."}],
            )
        key = storage.new_key()
        received.seek(0)
        storage.save(key, received)  # type: ignore[arg-type]

    document = ContractDocument(
        id=uuid.uuid4(),
        contract_id=contract.id,
        obligation_id=obligation.id if obligation else None,
        kind=kind,
        original_filename=_clean_filename(filename),
        file_type=file_type,
        mime_type=MIME_TYPES[file_type],
        size_bytes=size,
        sha256=sha256,
        storage_key=key,
        uploaded_by_id=current.id,
    )
    db.add(document)
    # Shown in the contract's activity: the document belongs to the contract (BR-09), evidence to its obligation.
    audit.record(
        db,
        AuditAction.OBLIGATION_EVIDENCE_ADDED if obligation else AuditAction.CONTRACT_DOCUMENT_UPLOADED,
        target_type=TargetType.OBLIGATION if obligation else TargetType.CONTRACT,
        target_id=obligation.id if obligation else contract.id,
        target_label=obligation.title if obligation else f"{contract.contract_number} · {contract.title}",
        actor_id=current.id,
        changes={"document": [None, document.original_filename]},
    )
    try:
        db.commit()
    except Exception:
        storage.delete(key)  # no record, no file: keep storage and database in step
        raise
    db.refresh(document)
    return document


def record_download(db: Session, current: CurrentUser, document: ContractDocument) -> None:
    """Who opened which original is part of the access trail for confidential contracts (NFR-SEC-05)."""
    audit.record(
        db,
        AuditAction.DOCUMENT_DOWNLOADED,
        target_type=TargetType.DOCUMENT,
        target_id=document.id,
        target_label=document.original_filename,
        actor_id=current.id,
    )
    db.commit()
