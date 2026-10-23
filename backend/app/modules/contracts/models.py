import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import AuditColumnsMixin, uuid_pk
from app.modules.parties.models import Party
from app.modules.properties.models import Property
from app.modules.users.models import User


class _Lookup:
    """Controlled list the business can extend or rename without a code change (FR-CON-06)."""

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name_en: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ContractType(_Lookup, Base):
    __tablename__ = "contract_types"


class ContractStatus(_Lookup, Base):
    __tablename__ = "contract_statuses"


# Which properties a contract covers (FR-PROP-01). A Property Manager's contracts are those on their properties.
contract_properties = Table(
    "contract_properties",
    Base.metadata,
    Column("contract_id", Uuid, ForeignKey("contracts.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "property_id", Uuid, ForeignKey("properties.id", ondelete="RESTRICT"), primary_key=True, index=True
    ),
)


class ContractParty(Base):
    """A party's part in a contract, e.g. landlord or tenant (FR-PARTY-03)."""

    __tablename__ = "contract_parties"

    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), primary_key=True
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(30))

    party: Mapped[Party] = relationship(lazy="joined")


class Contract(AuditColumnsMixin, Base):
    """A real estate contract (SRS 7.1 Contract, 7.2 fields; FR-CON-01..06)."""

    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="end_not_before_start"),  # BR-03
        CheckConstraint("(value_amount IS NULL) = (currency IS NULL)", name="value_has_currency"),
        CheckConstraint("value_amount IS NULL OR value_amount >= 0", name="value_not_negative"),
        CheckConstraint("contract_number = upper(contract_number)", name="number_uppercase"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    # Stored upper-cased, so "ct-2026-0142" and "CT-2026-0142" are the same contract.
    contract_number: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    contract_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contract_types.id"), index=True)
    status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contract_statuses.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)
    value_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    renewal_date: Mapped[date | None] = mapped_column(Date)  # decision D-09
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    archived_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    contract_type: Mapped[ContractType] = relationship(lazy="joined")
    status: Mapped[ContractStatus] = relationship(lazy="joined")
    parties: Mapped[list[ContractParty]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by=ContractParty.role
    )
    properties: Mapped[list[Property]] = relationship(
        secondary=contract_properties, lazy="selectin", order_by=Property.name
    )
    created_by: Mapped[User | None] = relationship(foreign_keys="Contract.created_by_id", lazy="joined")
    updated_by: Mapped[User | None] = relationship(foreign_keys="Contract.updated_by_id", lazy="joined")
