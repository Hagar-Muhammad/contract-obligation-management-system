import uuid

from sqlalchemy import CheckConstraint, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import AuditColumnsMixin, uuid_pk


class Party(AuditColumnsMixin, Base):
    """An individual or organization taking part in contracts (FR-PARTY-01, FR-PARTY-02)."""

    __tablename__ = "parties"
    __table_args__ = (
        CheckConstraint("party_type IN ('individual', 'organization')", name="party_type"),
        # Each type keeps only its own identifiers.
        CheckConstraint(
            "party_type = 'individual' OR (national_id IS NULL AND passport_no IS NULL)",
            name="organization_has_no_personal_ids",
        ),
        CheckConstraint(
            "party_type = 'organization' OR (registration_no IS NULL AND tax_no IS NULL)",
            name="individual_has_no_company_ids",
        ),
        # One official number, one party. Values are stored normalised (app/core/fields.py).
        Index(
            "uq_parties_national_id",
            "national_id",
            unique=True,
            postgresql_where=text("national_id IS NOT NULL"),
        ),
        Index(
            "uq_parties_passport_no",
            "passport_no",
            unique=True,
            postgresql_where=text("passport_no IS NOT NULL"),
        ),
        Index(
            "uq_parties_registration_no",
            "registration_no",
            unique=True,
            postgresql_where=text("registration_no IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    party_type: Mapped[str] = mapped_column(String(20))
    display_name: Mapped[str] = mapped_column(String(300), index=True)
    national_id: Mapped[str | None] = mapped_column(String(50))
    passport_no: Mapped[str | None] = mapped_column(String(50))
    registration_no: Mapped[str | None] = mapped_column(String(50))
    tax_no: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
