import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.pagination import Page, PageParams, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.parties import service
from app.modules.parties.schemas import PartyCreate, PartyRead, PartyType, PartyUpdate
from app.modules.users.rbac import Perm

router = APIRouter(tags=["parties"])

can_view = require_permission(Perm.CONTRACT_VIEW)
can_manage = require_permission(Perm.PARTY_MANAGE)
DUPLICATE: dict[int | str, dict[str, Any]] = {
    409: {"description": "Another party already has this ID or registration number"}
}


@router.get("/parties", response_model=Page[PartyRead], summary="List the parties visible to you")
def list_parties(
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200, description="Name, e-mail, phone, or an exact ID number."),
    party_type: PartyType | None = Query(None),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_view),
) -> Page[PartyRead]:
    parties, total = service.list_parties(db, current, params, q=q, party_type=party_type)
    return Page[PartyRead](
        items=[PartyRead.model_validate(p) for p in parties],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.post(
    "/parties",
    response_model=PartyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a party (FR-PARTY-01, FR-PARTY-02)",
    responses=DUPLICATE,
)
def create_party(
    payload: PartyCreate,
    response: Response,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_manage),
) -> PartyRead:
    party = service.create_party(db, current, payload)
    response.headers["Location"] = f"/api/v1/parties/{party.id}"
    return PartyRead.model_validate(party)


@router.get("/parties/{party_id}", response_model=PartyRead, summary="Get a party")
def get_party(
    party_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> PartyRead:
    return PartyRead.model_validate(service.get_party(db, current, party_id))


@router.patch(
    "/parties/{party_id}",
    response_model=PartyRead,
    summary="Update a party (FR-PARTY-01)",
    responses=DUPLICATE,
)
def update_party(
    party_id: uuid.UUID,
    payload: PartyUpdate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_manage),
) -> PartyRead:
    return PartyRead.model_validate(service.update_party(db, current, party_id, payload))
