import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.modules.contracts.schemas import PersonRef
from app.modules.documents.filetypes import FileType


class DocumentKind(StrEnum):
    CONTRACT = "contract"  # the signed contract itself ("Original" in the design)
    AMENDMENT = "amendment"
    ANNEX = "annex"
    OTHER = "other"


class DocumentRead(BaseModel):
    """Document metadata (FR-DOC-05). The file itself comes from GET /documents/{id}/download."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_id: uuid.UUID
    kind: DocumentKind
    original_filename: str
    file_type: FileType
    mime_type: str
    size_bytes: int
    sha256: str = Field(description="SHA-256 of the original, recorded at upload (FR-DOC-02).")
    uploaded_by: PersonRef
    uploaded_at: datetime


class UploadLimits(BaseModel):
    max_bytes: int
    allowed_types: list[FileType]
