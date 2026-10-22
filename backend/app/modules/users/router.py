import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.pagination import Page, PageParams, page_params
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.users import service
from app.modules.users.rbac import PENDING_CONFIRMATION, DataScope, Perm, RoleCode
from app.modules.users.schemas import RoleRead, UserCreate, UserRead, UserUpdate

router = APIRouter(tags=["users"])

can_manage_users = require_permission(Perm.USER_MANAGE)


@router.get("/users", response_model=Page[UserRead], summary="List users")
def list_users(
    params: PageParams = Depends(page_params),
    q: str | None = Query(None, max_length=200, description="Search name or e-mail."),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(can_manage_users),
) -> Page[UserRead]:
    users, total = service.list_users(db, params, q=q, is_active=is_active)
    return Page[UserRead](
        items=[UserRead.model_validate(u) for u in users],
        page=params.page,
        page_size=params.page_size,
        total=total,
    )


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account (FR-USER-01)",
)
def create_user(
    payload: UserCreate,
    response: Response,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_manage_users),
) -> UserRead:
    user = service.create_user(db, payload, actor_id=current.id)
    response.headers["Location"] = f"/api/v1/users/{user.id}"
    return UserRead.model_validate(user)


@router.get("/users/{user_id}", response_model=UserRead, summary="Get a user")
def get_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), _: CurrentUser = Depends(can_manage_users)
) -> UserRead:
    return UserRead.model_validate(service.get_user(db, user_id))


@router.patch(
    "/users/{user_id}", response_model=UserRead, summary="Update user information and roles (FR-USER-02)"
)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(can_manage_users),
) -> UserRead:
    return UserRead.model_validate(service.update_user(db, user_id, payload, actor_id=current.id))


@router.post("/users/{user_id}/deactivate", response_model=UserRead, summary="Deactivate a user (FR-USER-03)")
def deactivate_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_manage_users)
) -> UserRead:
    return UserRead.model_validate(service.set_active(db, user_id, False, actor_id=current.id))


@router.post("/users/{user_id}/activate", response_model=UserRead, summary="Re-activate a user")
def activate_user(
    user_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(can_manage_users)
) -> UserRead:
    return UserRead.model_validate(service.set_active(db, user_id, True, actor_id=current.id))


@router.get("/roles", response_model=list[RoleRead], summary="List roles and their permissions")
def list_roles(db: Session = Depends(get_db), _: CurrentUser = Depends(can_manage_users)) -> list[RoleRead]:
    return [
        RoleRead(
            code=r.code,
            name=r.name,
            description=r.description,
            data_scope=DataScope(r.data_scope),
            permissions=sorted(p.code for p in r.permissions),
            scoped_permissions=sorted(PENDING_CONFIRMATION.get(RoleCode(r.code), frozenset())),
        )
        for r in service.list_roles(db)
    ]
