"""Writing and reading the audit trail (FR-AUD-01..03).

Services call `record()` for every important change, before they commit, so the audit record is saved in the same
transaction as the change: a change that is rolled back leaves no record, and a saved change always has one.
"""

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.pagination import PageParams, paginate
from app.core.request_context import current_client_ip, current_request_id
from app.modules.audit.actions import ActorType, AuditAction, TargetType
from app.modules.audit.models import AuditLog
from app.modules.users.models import User


def record(
    db: Session,
    action: AuditAction,
    *,
    target_type: TargetType,
    target_id: uuid.UUID | None,
    target_label: str | None = None,
    actor_id: uuid.UUID | None = None,
    actor_type: ActorType | None = None,
    changes: Mapping[str, Any] | None = None,
) -> AuditLog:
    """Add an audit record to the caller's transaction. Never commits; the caller does."""
    entry = AuditLog(
        action=action,
        actor_user_id=actor_id,
        actor_type=actor_type or (ActorType.USER if actor_id else ActorType.SYSTEM),
        target_type=target_type,
        target_id=target_id,
        target_label=target_label[:300] if target_label else None,
        changes=dict(changes) if changes else None,
        request_id=current_request_id(),
        ip_address=current_client_ip(),
    )
    db.add(entry)
    return entry


def changes_between(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, list[Any]]:
    """`{field: [old, new]}` for every field whose value differs."""
    return {field: [before.get(field), value] for field, value in after.items() if before.get(field) != value}


def list_audit_logs(
    db: Session,
    params: PageParams,
    *,
    q: str | None = None,
    action: AuditAction | None = None,
    target_type: TargetType | None = None,
    target_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> tuple[list[AuditLog], int]:
    """Newest first. `q` matches the actor's name or e-mail, or the target's name."""
    stmt = (
        select(AuditLog)
        .outerjoin(User, AuditLog.actor_user_id == User.id)
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
    )
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(pattern), User.email.ilike(pattern), AuditLog.target_label.ilike(pattern)
            )
        )
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if target_type is not None:
        stmt = stmt.where(AuditLog.target_type == target_type)
    if target_id is not None:
        stmt = stmt.where(AuditLog.target_id == target_id)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_id)
    if occurred_from is not None:
        stmt = stmt.where(AuditLog.occurred_at >= occurred_from)
    if occurred_to is not None:
        stmt = stmt.where(AuditLog.occurred_at < occurred_to)
    return paginate(db, stmt, params)
