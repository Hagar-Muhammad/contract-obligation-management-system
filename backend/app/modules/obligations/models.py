import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import AuditColumnsMixin, uuid_pk
from app.modules.contracts.models import Contract
from app.modules.parties.models import Party
from app.modules.users.models import User


class Obligation(AuditColumnsMixin, Base):
    """A contractual duty (SRS 7.1 Obligation, 7.3 fields; FR-OBL-01..07).

    `status` is what people set: pending, in progress, completed or cancelled. Overdue (BR-04) is derived from the
    due date, so it is always correct; `overdue_at` records when the daily job first saw it overdue.
    A recurring obligation is a series: every occurrence is a row, all sharing `series_id` (the first one's id).
    """

    __tablename__ = "obligations"
    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name="priority"),
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'cancelled')", name="status"),
        CheckConstraint(
            "start_date IS NULL OR due_date IS NULL OR due_date >= start_date", name="due_not_before_start"
        ),
        CheckConstraint("recurrence_rule IS NULL OR due_date IS NOT NULL", name="recurring_has_due_date"),
        Index("ix_obligations_status_due_date", "status", "due_date"),
        Index("ix_obligations_responsible_user_status", "responsible_user_id", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    # BR-01: every obligation belongs to a contract.
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    responsible_party_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parties.id", ondelete="RESTRICT"), index=True
    )
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))
    # RFC 5545 RRULE, e.g. "FREQ=MONTHLY;INTERVAL=3" (BR-08). Counted from the series' first due date.
    recurrence_rule: Mapped[str | None] = mapped_column(String(500))
    series_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    penalty_text: Mapped[str | None] = mapped_column(Text)  # decision D-08
    notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    overdue_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contract: Mapped[Contract] = relationship(lazy="joined", innerjoin=True)
    responsible_party: Mapped[Party] = relationship(lazy="joined", innerjoin=True)
    responsible_user: Mapped[User | None] = relationship(foreign_keys=[responsible_user_id], lazy="joined")
