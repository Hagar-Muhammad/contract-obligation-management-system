"""User administration (FR-USER-01..03) and self sign-up (CR-01).

Administration functions assume the caller was already checked for `user:manage`.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.pagination import PageParams, paginate
from app.core.security import hash_password
from app.modules.auth.service import revoke_all_sessions
from app.modules.users.models import Role, User
from app.modules.users.rbac import RoleCode
from app.modules.users.schemas import SignUpRequest, UserCreate, UserUpdate


def _roles_by_code(db: Session, codes: Sequence[RoleCode]) -> list[Role]:
    wanted = {str(c) for c in codes}
    roles = list(db.scalars(select(Role).where(Role.code.in_(wanted))))
    missing = wanted - {r.code for r in roles}
    if missing:
        raise BusinessRuleError("Unknown role(s).", details=sorted(missing))
    return roles


def _ensure_email_free(db: Session, email: str, *, except_id: uuid.UUID | None = None) -> None:
    stmt = select(User.id).where(User.email == email)
    if except_id is not None:
        stmt = stmt.where(User.id != except_id)
    if db.scalar(stmt) is not None:
        raise ConflictError("A user with this e-mail already exists.", details=[{"field": "body.email"}])


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def list_users(
    db: Session, params: PageParams, *, q: str | None = None, is_active: bool | None = None
) -> tuple[list[User], int]:
    stmt = select(User).order_by(User.full_name, User.email)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    return paginate(db, stmt, params)


def create_user(db: Session, data: UserCreate, *, actor_id: uuid.UUID) -> User:
    _ensure_email_free(db, data.email)
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        preferred_language=data.preferred_language,
        roles=_roles_by_code(db, data.role_codes),
        created_by_id=actor_id,
        updated_by_id=actor_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def register_self(db: Session, data: SignUpRequest) -> User:
    """Self sign-up (CR-01): the new account gets only the configured low-privilege role."""
    settings = get_settings()
    if not settings.self_signup_enabled:
        raise ForbiddenError("Self sign-up is disabled. Ask an administrator for an account.")
    _ensure_email_free(db, data.email)
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        preferred_language=data.preferred_language,
        roles=_roles_by_code(db, [RoleCode(settings.self_signup_role)]),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: uuid.UUID, data: UserUpdate, *, actor_id: uuid.UUID) -> User:
    user = get_user(db, user_id)
    if data.email is not None and data.email != user.email:
        _ensure_email_free(db, data.email, except_id=user.id)
        user.email = data.email
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.preferred_language is not None:
        user.preferred_language = data.preferred_language
    if data.role_codes is not None:
        if (
            user.id == actor_id
            and RoleCode.ADMIN in user.role_codes
            and RoleCode.ADMIN not in data.role_codes
        ):
            raise BusinessRuleError("You cannot remove your own Administrator role.")
        user.roles = _roles_by_code(db, data.role_codes)
    if data.password is not None:
        user.password_hash = hash_password(data.password)
        revoke_all_sessions(db, user.id)
    user.updated_by_id = actor_id
    db.commit()
    db.refresh(user)
    return user


def set_active(db: Session, user_id: uuid.UUID, active: bool, *, actor_id: uuid.UUID) -> User:
    user = get_user(db, user_id)
    if not active and user.id == actor_id:
        raise BusinessRuleError("You cannot deactivate your own account.")
    user.is_active = active
    user.updated_by_id = actor_id
    if not active:
        revoke_all_sessions(db, user.id)  # FR-USER-03: takes effect immediately, not at token expiry.
    db.commit()
    db.refresh(user)
    return user


def list_roles(db: Session) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.name)))
