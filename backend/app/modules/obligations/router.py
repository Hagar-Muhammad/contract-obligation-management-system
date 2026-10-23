import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.pagination import Page, PageParams, page_params
from app.core.storage import StorageBackend, get_storage
from app.modules.audit import service as audit_service
from app.modules.audit.actions import TargetType
from app.modules.audit.schemas import ActivityRead
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.documents import service as documents_service
from app.modules.documents.models import ContractDocument
from app.modules.documents.schemas import DocumentKind, DocumentRead
from app.modules.obligations import service
from app.modules.obligations.models import Obligation
from app.modules.obligations.schemas import (
    ContractRef,
    ObligationCounts,
    ObligationCreate,
    ObligationRead,
    ObligationSort,
    ObligationUpdate,
    ObligationView,
    PartyRef,
    Priority,
    StatusChange,
    UserRef,
)
from app.modules.users.rbac import Perm

router = APIRouter(tags=["obligations"])

can_view = require_permission(Perm.OBLIGATION_VIEW)
can_create = require_permission(Perm.OBLIGATION_CREATE)
can_update = require_permission(Perm.OBLIGATION_UPDATE)
can_view_evidence = require_permission(Perm.OBLIGATION_VIEW, Perm.DOCUMENT_VIEW)
can_add_evidence = require_permission(Perm.OBLIGATION_UPDATE, Perm.DOCUMENT_UPLOAD)
UPLOAD_ERRORS: dict[int | str, dict[str, Any]] = {
    413: {"description": "The file is larger than the limit"},
    415: {"description": "The file type is not supported"},
}


def _read(obligation: Obligation, evidence: int = 0) -> ObligationRead:
    return ObligationRead(
        id=obligation.id,
        contract=ContractRef.model_validate(obligation.contract),
        title=obligation.title,
        description=obligation.description,
        responsible_party=PartyRef.model_validate(obligation.responsible_party),
        responsible_user=UserRef.model_validate(obligation.responsible_user)
        if obligation.responsible_user
        else None,
        start_date=obligation.start_date,
        due_date=obligation.due_date,
        priority=Priority(obligation.priority),
        status=obligation.status,
        effective_status=service.effective_status(obligation),
        recurrence_rule=obligation.recurrence_rule,
        series_id=obligation.series_id,
        penalty_text=obligation.penalty_text,
        notes=obligation.notes,
        completed_at=obligation.completed_at,
        cancelled_at=obligation.cancelled_at,
        overdue_at=obligation.overdue_at,
        evidence_count=evidence,
        created_at=obligation.created_at,
        updated_at=obligation.updated_at,
    )


def _read_one(db: Session, obligation: Obligation) -> ObligationRead:
    return _read(obligation, service.evidence_counts(db, [obligation.id]).get(obligation.id, 0))


@router.get("/obligations", response_model=Page[ObligationRead], summary="List obligations (FR-OBL-07)")
def list_obligations(
    params: PageParams = Depends(page_params),
    view: ObligationView | None = Query(None, description="Status chip. Without it: every obligation."),
    q: str | None = Query(
        None, max_length=200, description="Title, contract number/title or responsible party."
    ),
    contract_id: uuid.UUID | None = Query(None),
    property_id: uuid.UUID | None = Query(
        None, description="Obligations of this property's contracts (FR-PROP-02)."
    ),
    party_id: uuid.UUID | None = Query(None, description="Responsible party."),
    responsible_user_id: uuid.UUID | None = Query(None),
    mine: bool = Query(False, description="Only obligations assigned to me."),
    priority: Priority | None = Query(None),
    due_from: date | None = Query(None),
    due_to: date | None = Query(None),
    sort: ObligationSort = Query(ObligationSort.DUE_DATE),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_view),
) -> Page[ObligationRead]:
    obligations, total = service.list_obligations(
        db,
        current,
        params,
        view=view,
        q=q,
        contract_id=contract_id,
        property_id=property_id,
        party_id=party_id,
        responsible_user_id=current.id if mine else responsible_user_id,
        priority=priority,
        due_from=due_from,
        due_to=due_to,
        sort=sort,
    )
    evidence = service.evidence_counts(db, [o.id for o in obligations])
    return Page[ObligationRead](
        items=[_read(o, evidence.get(o.id, 0)) for o in obligations],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get(
    "/obligations/counts", response_model=ObligationCounts, summary="Number of obligations per status chip"
)
def count_obligations(
    db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> ObligationCounts:
    return service.count_by_view(db, current)


@router.post(
    "/obligations",
    response_model=ObligationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an obligation on a contract (FR-OBL-01..03, BR-01)",
)
def create_obligation(
    payload: ObligationCreate,
    response: Response,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_create),
) -> ObligationRead:
    obligation = service.create_obligation(db, current, payload)
    response.headers["Location"] = f"/api/v1/obligations/{obligation.id}"
    return _read(obligation)


@router.get("/obligations/{obligation_id}", response_model=ObligationRead, summary="Get an obligation")
def get_obligation(
    obligation_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> ObligationRead:
    return _read_one(db, service.get_obligation(db, current, obligation_id))


@router.patch(
    "/obligations/{obligation_id}", response_model=ObligationRead, summary="Edit an obligation's details"
)
def update_obligation(
    obligation_id: uuid.UUID,
    payload: ObligationUpdate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_update),
) -> ObligationRead:
    return _read_one(db, service.update_obligation(db, current, obligation_id, payload))


@router.post(
    "/obligations/{obligation_id}/status",
    response_model=ObligationRead,
    summary="Change an obligation's status, with an optional note (FR-OBL-04)",
)
def change_status(
    obligation_id: uuid.UUID,
    payload: StatusChange,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_update),
) -> ObligationRead:
    return _read_one(db, service.change_status(db, current, obligation_id, payload))


@router.get(
    "/obligations/{obligation_id}/activity",
    response_model=list[ActivityRead],
    summary="Latest changes to an obligation",
)
def obligation_activity(
    obligation_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> list[ActivityRead]:
    obligation = service.get_obligation(db, current, obligation_id)
    entries = audit_service.list_activity(db, TargetType.OBLIGATION, obligation.id)
    return [ActivityRead.model_validate(e) for e in entries]


@router.get(
    "/obligations/{obligation_id}/evidence",
    response_model=list[DocumentRead],
    summary="Evidence attached to an obligation (SRS 7.3)",
)
def list_evidence(
    obligation_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view_evidence)
) -> list[DocumentRead]:
    obligation = service.get_obligation(db, current, obligation_id)
    documents = db.scalars(
        select(ContractDocument)
        .where(ContractDocument.obligation_id == obligation.id)
        .order_by(ContractDocument.uploaded_at.desc())
    )
    return [DocumentRead.model_validate(d) for d in documents]


@router.post(
    "/obligations/{obligation_id}/evidence",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Attach evidence to an obligation, e.g. a certificate (SRS 7.3)",
    responses=UPLOAD_ERRORS,
)
def add_evidence(
    obligation_id: uuid.UUID,
    file: UploadFile = File(description="PDF, DOCX, PNG or JPG (decision D-12)."),
    db: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    current: CurrentUser = Depends(can_add_evidence),
) -> DocumentRead:
    obligation = service.get_obligation(db, current, obligation_id)
    document = documents_service.upload(
        db,
        storage,
        current,
        obligation.contract_id,
        file.file,
        file.filename,
        DocumentKind.EVIDENCE,
        obligation=obligation,
    )
    return DocumentRead.model_validate(document)
