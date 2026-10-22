import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.pagination import Page, PageParams, page_params
from app.modules.audit import service
from app.modules.audit.actions import AuditAction, TargetType
from app.modules.audit.schemas import AuditLogRead
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.users.rbac import Perm

# Read-only on purpose: there is no endpoint that changes or deletes audit records (FR-AUD-03).
router = APIRouter(tags=["audit"])


@router.get(
    "/audit-logs", response_model=Page[AuditLogRead], summary="List audit records, newest first (FR-AUD-02)"
)
def list_audit_logs(
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200, description="Search actor name/e-mail or target name."),
    action: AuditAction | None = Query(None),
    target_type: TargetType | None = Query(None),
    target_id: uuid.UUID | None = Query(None),
    actor_id: uuid.UUID | None = Query(None),
    occurred_from: datetime | None = Query(None, description="Inclusive lower bound (ISO 8601)."),
    occurred_to: datetime | None = Query(None, description="Exclusive upper bound (ISO 8601)."),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_permission(Perm.AUDIT_VIEW)),
) -> Page[AuditLogRead]:
    entries, total = service.list_audit_logs(
        db,
        params,
        q=q,
        action=action,
        target_type=target_type,
        target_id=target_id,
        actor_id=actor_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    return Page[AuditLogRead](
        items=[AuditLogRead.model_validate(e) for e in entries],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )
