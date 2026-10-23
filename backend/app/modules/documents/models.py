import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import uuid_pk
from app.modules.users.models import User


class ContractDocument(Base):
    """An uploaded file and its metadata (SRS 7.1 ContractDocument, FR-DOC-01..05).

    The original file is write-once (FR-DOC-02): nothing in the application changes or deletes it, and the SHA-256
    recorded at upload proves it is unchanged.
    """

    __tablename__ = "contract_documents"
    __table_args__ = (
        CheckConstraint("kind IN ('contract', 'amendment', 'annex', 'evidence', 'other')", name="kind"),
        CheckConstraint("(kind = 'evidence') = (obligation_id IS NOT NULL)", name="evidence_has_obligation"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    # BR-09: every document belongs to a contract.
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="RESTRICT"), index=True
    )
    # Evidence for an obligation (7.3 Evidence/Attachment); the obligation belongs to the same contract.
    obligation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("obligations.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    # Opaque key in the storage backend; never a public URL, never shown to users.
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    uploaded_by: Mapped[User] = relationship(lazy="joined")
