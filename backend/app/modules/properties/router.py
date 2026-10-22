import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.pagination import Page, PageParams, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.properties import service
from app.modules.properties.schemas import (
    PropertyCreate,
    PropertyManagerRead,
    PropertyRead,
    PropertyType,
    PropertyUpdate,
)
from app.modules.users.rbac import Perm

router = APIRouter(tags=["properties"])

can_view = require_permission(Perm.CONTRACT_VIEW)
can_manage = require_permission(Perm.PROPERTY_MANAGE)
DUPLICATE: dict[int | str, dict[str, Any]] = {409: {"description": "Another property already uses this code"}}


@router.get("/properties", response_model=Page[PropertyRead], summary="List the properties visible to you")
def list_properties(
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200, description="Code, name, city or address."),
    property_type: PropertyType | None = Query(None),
    manager_id: uuid.UUID | None = Query(None, description="Only properties assigned to this user."),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_view),
) -> Page[PropertyRead]:
    props, total = service.list_properties(
        db, current, params, q=q, property_type=property_type, manager_id=manager_id
    )
    return Page[PropertyRead](
        items=[PropertyRead.model_validate(p) for p in props],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.post(
    "/properties",
    response_model=PropertyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a property and assign its managers",
    responses=DUPLICATE,
)
def create_property(
    payload: PropertyCreate,
    response: Response,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_manage),
) -> PropertyRead:
    prop = service.create_property(db, current, payload)
    response.headers["Location"] = f"/api/v1/properties/{prop.id}"
    return PropertyRead.model_validate(prop)


# Declared before /properties/{property_id} so the path is not read as an id.
@router.get(
    "/properties/assignable-managers",
    response_model=list[PropertyManagerRead],
    summary="Active Property Managers who can be assigned to a property",
)
def list_assignable_managers(
    q: str | None = Query(None, max_length=200, description="Name or e-mail."),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(can_manage),
) -> list[PropertyManagerRead]:
    return [PropertyManagerRead.model_validate(u) for u in service.list_assignable_managers(db, q=q)]


@router.get("/properties/{property_id}", response_model=PropertyRead, summary="Get a property")
def get_property(
    property_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_view)
) -> PropertyRead:
    return PropertyRead.model_validate(service.get_property(db, current, property_id))


@router.patch(
    "/properties/{property_id}",
    response_model=PropertyRead,
    summary="Update a property or its assigned managers",
    responses=DUPLICATE,
)
def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_manage),
) -> PropertyRead:
    return PropertyRead.model_validate(service.update_property(db, current, property_id, payload))
