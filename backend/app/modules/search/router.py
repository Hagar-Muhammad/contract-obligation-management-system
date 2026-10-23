"""Search across contracts, parties, properties and obligations from the top bar (FR-SEARCH-01, design top bar).

Each group reuses that module's own list query, so scope, permissions and Arabic-aware matching are the same as on
the list pages; a group the user may not see is simply empty.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.pagination import PageParams
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.contracts import service as contracts_service
from app.modules.obligations import service as obligations_service
from app.modules.obligations.schemas import EffectiveStatus
from app.modules.parties import service as parties_service
from app.modules.parties.schemas import PartyType
from app.modules.properties import service as properties_service
from app.modules.users.rbac import Perm

router = APIRouter(tags=["search"])


class ContractHit(BaseModel):
    id: uuid.UUID
    contract_number: str
    title: str


class PartyHit(BaseModel):
    id: uuid.UUID
    display_name: str
    party_type: PartyType


class PropertyHit(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class ObligationHit(BaseModel):
    id: uuid.UUID
    title: str
    contract_number: str
    due_date: date | None
    effective_status: EffectiveStatus


class SearchResults(BaseModel):
    contracts: list[ContractHit]
    parties: list[PartyHit]
    properties: list[PropertyHit]
    obligations: list[ObligationHit]


@router.get("/search", response_model=SearchResults, summary="Search everything you can see (top bar)")
def search(
    q: str = Query(min_length=2, max_length=200, description="At least two characters."),
    limit: int = Query(5, ge=1, le=20, description="Results per group."),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_permission(Perm.CONTRACT_VIEW)),
) -> SearchResults:
    page = PageParams(page=1, page_size=limit)
    contracts, _ = contracts_service.list_contracts(db, current, page, q=q)
    parties, _ = parties_service.list_parties(db, current, page, q=q)
    properties, _ = properties_service.list_properties(db, current, page, q=q)
    obligations = (
        obligations_service.list_obligations(db, current, page, q=q)[0]
        if current.has(Perm.OBLIGATION_VIEW)
        else []
    )
    return SearchResults(
        contracts=[ContractHit(id=c.id, contract_number=c.contract_number, title=c.title) for c in contracts],
        parties=[
            PartyHit(id=p.id, display_name=p.display_name, party_type=PartyType(p.party_type))
            for p in parties
        ],
        properties=[PropertyHit(id=p.id, code=p.code, name=p.name) for p in properties],
        obligations=[
            ObligationHit(
                id=o.id,
                title=o.title,
                contract_number=o.contract.contract_number,
                due_date=o.due_date,
                effective_status=obligations_service.effective_status(o),
            )
            for o in obligations
        ],
    )
