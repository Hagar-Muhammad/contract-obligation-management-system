import uuid
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.storage import StorageBackend, get_storage, iter_file
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.documents import service
from app.modules.documents.filetypes import FileType
from app.modules.documents.schemas import DocumentKind, DocumentRead, UploadLimits
from app.modules.users.rbac import Perm

router = APIRouter(tags=["documents"])

can_view = require_permission(Perm.CONTRACT_VIEW, Perm.DOCUMENT_VIEW)
can_upload = require_permission(Perm.CONTRACT_VIEW, Perm.DOCUMENT_UPLOAD)
UPLOAD_ERRORS: dict[int | str, dict[str, Any]] = {
    413: {"description": "The file is larger than the limit"},
    415: {"description": "The file type is not supported"},
}


def _content_disposition(filename: str) -> str:
    """Attachment header that survives non-ASCII names (RFC 6266 / RFC 5987)."""
    _, dot, ext = filename.rpartition(".")
    ascii_name = "".join(ch for ch in filename if ch.isascii() and (ch.isalnum() or ch in "._- ")).strip(" .")
    if not ascii_name or ascii_name.lower() == ext.lower():
        ascii_name = f"document.{ext}" if dot and ext.isascii() else "document"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


@router.get("/documents/limits", response_model=UploadLimits, summary="Allowed file types and size (D-12)")
def upload_limits(_: CurrentUser = Depends(can_view)) -> UploadLimits:
    settings = get_settings()
    return UploadLimits(
        max_bytes=settings.upload_max_bytes,
        allowed_types=[FileType(t) for t in settings.upload_allowed_types],
    )


@router.get(
    "/contracts/{contract_id}/documents",
    response_model=list[DocumentRead],
    summary="A contract's documents, newest first (FR-DOC-05)",
)
def list_documents(
    contract_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> list[DocumentRead]:
    return [DocumentRead.model_validate(d) for d in service.list_documents(db, current, contract_id)]


@router.post(
    "/contracts/{contract_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document to a contract (FR-DOC-01, FR-DOC-04)",
    responses=UPLOAD_ERRORS,
)
def upload_document(
    contract_id: uuid.UUID,
    response: Response,
    file: UploadFile = File(description="PDF, DOCX, PNG or JPG (decision D-12)."),
    kind: DocumentKind = Form(DocumentKind.OTHER),
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    current: CurrentUser = Depends(can_upload),
) -> DocumentRead:
    document = service.upload(db, storage, current, contract_id, file.file, file.filename, kind)
    response.headers["Location"] = f"/api/v1/documents/{document.id}"
    return DocumentRead.model_validate(document)


@router.get("/documents/{document_id}", response_model=DocumentRead, summary="Document metadata (FR-DOC-05)")
def get_document(
    document_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> DocumentRead:
    return DocumentRead.model_validate(service.get_document(db, current, document_id))


@router.get(
    "/documents/{document_id}/download",
    response_class=StreamingResponse,
    summary="Download the original file (FR-DOC-02, FR-DOC-03, NFR-SEC-05)",
    responses={200: {"content": {"application/octet-stream": {}}, "description": "The original file"}},
)
def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    current: CurrentUser = Depends(can_view),
) -> StreamingResponse:
    document = service.get_document(db, current, document_id)
    handle = storage.open(document.storage_key)
    service.record_download(db, current, document)
    return StreamingResponse(
        iter_file(handle),
        media_type=document.mime_type,
        headers={
            "Content-Disposition": _content_disposition(document.original_filename),
            "Content-Length": str(document.size_bytes),
            "Cache-Control": "private, no-store",
            # The browser must never run anything from an uploaded file.
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )
