import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import uuid_pk
from app.modules.users.models import User


class AuditLog(Base):
    """One recorded action (FR-AUD-01, FR-AUD-02). Append-only: a trigger rejects UPDATE/DELETE (FR-AUD-03)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'system', 'anonymous')", name="actor_type"),
        CheckConstraint(
            "(actor_type = 'user') = (actor_user_id IS NOT NULL)", name="actor_user_matches_type"
        ),
        Index("ix_audit_logs_target", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    # clock_timestamp(), not now(): several records written in one transaction keep their real order.
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp(), index=True
    )
    # RESTRICT: users are deactivated, never deleted, and a SET NULL cascade would be an UPDATE the trigger blocks.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    actor_type: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    # The target's name when the action happened, so the log stays readable after renames.
    target_label: Mapped[str | None] = mapped_column(String(300))
    # {field: [old, new]} for changed fields (FR-AUD-02).
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(45))

    actor: Mapped[User | None] = relationship(lazy="joined")
