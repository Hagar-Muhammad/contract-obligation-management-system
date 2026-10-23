import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.pagination import Page, PageParams, page_params
from app.modules.audit import service as audit_service
from app.modules.audit.actions import TargetType
from app.modules.audit.schemas import ActivityRead
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.contracts import service
from app.modules.contracts.models import Contract, ContractStatus
from app.modules.contracts.schemas import (
    STATUS_TRANSITIONS,
    ContractCounts,
    ContractCreate,
    ContractDefaults,
    ContractPartyRead,
    ContractPropertyRead,
    ContractRead,
    ContractSort,
    ContractStatusRead,
    ContractUpdate,
    ContractView,
    LookupRead,
    ObligationSummary,
    PersonRef,
    StatusCode,
)
from app.modules.contracts.scope import obligation_in_scope
from app.modules.obligations import service as obligations_service
from app.modules.obligations.models import Obligation
from app.modules.users.rbac import Perm

router = APIRouter(tags=["contracts"])

can_view = require_permission(Perm.CONTRACT_VIEW)
can_create = require_permission(Perm.CONTRACT_CREATE)
can_edit = require_permission(Perm.CONTRACT_EDIT)
can_archive = require_permission(Perm.CONTRACT_ARCHIVE)
DUPLICATE: dict[int | str, dict[str, Any]] = {409: {"description": "The contract number is already used"}}


def _read_one(db: Session, current: CurrentUser, contract: Contract) -> ContractRead:
    return _read(contract, obligations_service.contract_summaries(db, current, [contract.id])[contract.id])


def _status(row: ContractStatus) -> ContractStatusRead:
    return ContractStatusRead(
        code=row.code,
        name_en=row.name_en,
        name_ar=row.name_ar,
        next_codes=sorted(STATUS_TRANSITIONS.get(StatusCode(row.code), frozenset())),
    )


def _read(contract: Contract, summary: ObligationSummary) -> ContractRead:
    return ContractRead(
        id=contract.id,
        contract_number=contract.contract_number,
        title=contract.title,
        contract_type=LookupRead.model_validate(contract.contract_type),
        status=_status(contract.status),
        description=contract.description,
        start_date=contract.start_date,
        end_date=contract.end_date,
        value_amount=contract.value_amount,
        currency=contract.currency,
        renewal_date=contract.renewal_date,
        parties=[
            ContractPartyRead(
                id=link.party.id,
                display_name=link.party.display_name,
                party_type=link.party.party_type,
                role=link.role,
            )
            for link in contract.parties
        ],
        properties=[ContractPropertyRead.model_validate(p) for p in contract.properties],
        archived_at=contract.archived_at,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
        created_by=PersonRef.model_validate(contract.created_by) if contract.created_by else None,
        updated_by=PersonRef.model_validate(contract.updated_by) if contract.updated_by else None,
        obligations=summary,
    )


@router.get("/contract-types", response_model=list[LookupRead], summary="Active contract types (FR-CON-06)")
def list_contract_types(
    db: Session = Depends(get_db), _: CurrentUser = Depends(can_view)
) -> list[LookupRead]:
    return [LookupRead.model_validate(t) for t in service.list_types(db)]


@router.get(
    "/contract-statuses",
    response_model=list[ContractStatusRead],
    summary="Contract statuses and their allowed transitions (FR-CON-06, D-17)",
)
def list_contract_statuses(
    db: Session = Depends(get_db), _: CurrentUser = Depends(can_view)
) -> list[ContractStatusRead]:
    return [_status(s) for s in service.list_statuses(db)]


@router.get("/contracts", response_model=Page[ContractRead], summary="List the contracts visible to you")
def list_contracts(
    params: PageParams = Depends(page_params),
    view: ContractView | None = Query(
        None, description="List tab. Without it: every contract not archived (BR-07)."
    ),
    q: str | None = Query(
        None, max_length=200, description="Number, title, party name, or property name/code."
    ),
    type_code: str | None = Query(None, max_length=50),
    status_code: list[StatusCode] = Query([], description="One or more statuses (FR-SEARCH-02)."),
    party_id: uuid.UUID | None = Query(None),
    property_id: uuid.UUID | None = Query(None, description="Contracts on this property (FR-PROP-02)."),
    term_from: date | None = Query(None, description="Contracts in force on or after this date."),
    term_to: date | None = Query(None, description="Contracts in force on or before this date."),
    sort: ContractSort = Query(ContractSort.END_DATE),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_view),
) -> Page[ContractRead]:
    contracts, total = service.list_contracts(
        db,
        current,
        params,
        view=view,
        q=q,
        type_code=type_code,
        status_codes=status_code,
        party_id=party_id,
        property_id=property_id,
        term_from=term_from,
        term_to=term_to,
        sort=sort,
    )
    summaries = obligations_service.contract_summaries(db, current, [c.id for c in contracts])
    return Page[ContractRead](
        items=[_read(c, summaries[c.id]) for c in contracts],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.get("/contracts/counts", response_model=ContractCounts, summary="Number of contracts per list tab")
def count_contracts(
    db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> ContractCounts:
    return service.count_by_view(db, current)


@router.get(
    "/contracts/defaults", response_model=ContractDefaults, summary="Suggested values for a new contract"
)
def contract_defaults(db: Session = Depends(get_db), _: CurrentUser = Depends(can_view)) -> ContractDefaults:
    settings = get_settings()
    return ContractDefaults(
        next_number=service.next_number(db),
        default_currency=settings.default_currency,
        expiring_soon_days=settings.expiring_soon_days,
    )


@router.post(
    "/contracts",
    response_model=ContractRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a contract (FR-CON-01, FR-CON-02)",
    responses=DUPLICATE,
)
def create_contract(
    payload: ContractCreate,
    response: Response,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_create),
) -> ContractRead:
    contract = service.create_contract(db, current, payload)
    response.headers["Location"] = f"/api/v1/contracts/{contract.id}"
    return _read_one(db, current, contract)


@router.get("/contracts/{contract_id}", response_model=ContractRead, summary="Contract details (FR-CON-03)")
def get_contract(
    contract_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> ContractRead:
    return _read_one(db, current, service.get_contract(db, current, contract_id))


@router.patch(
    "/contracts/{contract_id}",
    response_model=ContractRead,
    summary="Edit a contract, its status, parties or properties (FR-CON-04)",
    responses=DUPLICATE,
)
def update_contract(
    contract_id: uuid.UUID,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_edit),
) -> ContractRead:
    return _read_one(db, current, service.update_contract(db, current, contract_id, payload))


@router.post(
    "/contracts/{contract_id}/archive", response_model=ContractRead, summary="Archive a contract (FR-CON-05)"
)
def archive_contract(
    contract_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_archive)
) -> ContractRead:
    return _read_one(db, current, service.set_archived(db, current, contract_id, True))


@router.post(
    "/contracts/{contract_id}/restore", response_model=ContractRead, summary="Restore an archived contract"
)
def restore_contract(
    contract_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_archive)
) -> ContractRead:
    return _read_one(db, current, service.set_archived(db, current, contract_id, False))


@router.get(
    "/contracts/{contract_id}/activity",
    response_model=list[ActivityRead],
    summary="Latest changes to a contract, for everyone who can see it",
)
def contract_activity(
    contract_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> list[ActivityRead]:
    contract = service.get_contract(db, current, contract_id)
    obligation_ids = select(Obligation.id).where(
        Obligation.contract_id == contract.id, obligation_in_scope(current)
    )
    entries = audit_service.list_activity(
        db, TargetType.CONTRACT, contract.id, related=(TargetType.OBLIGATION, obligation_ids)
    )
    return [ActivityRead.model_validate(e) for e in entries]
