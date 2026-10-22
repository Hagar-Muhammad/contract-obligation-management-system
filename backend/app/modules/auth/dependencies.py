"""Authentication and authorization dependencies for routers (FR-AUTH-02, FR-AUTH-03, NFR-SEC-01, NFR-SEC-02)."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import InvalidTokenError, decode_access_token
from app.modules.auth.models import UserSession
from app.modules.users.models import User
from app.modules.users.rbac import Perm

bearer_scheme = HTTPBearer(
    auto_error=False, description="Access token from POST /auth/login or /auth/refresh."
)


@dataclass(frozen=True)
class CurrentUser:
    user: User
    session_id: uuid.UUID

    @property
    def id(self) -> uuid.UUID:
        return self.user.id

    @property
    def permissions(self) -> set[str]:
        return self.user.permission_codes

    def has(self, permission: Perm) -> bool:
        return permission in self.permissions


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Resolve the caller from the bearer token; reject anything not backed by a live session and active user."""
    if credentials is None:
        raise UnauthorizedError("Authentication required.")
    try:
        user_id, session_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired access token.") from exc

    session = db.get(UserSession, session_id)
    if (
        session is None
        or session.user_id != user_id
        or session.revoked_at is not None
        or session.expires_at <= datetime.now(UTC)
    ):
        raise UnauthorizedError("Session has ended. Please log in again.")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is not active.")
    return CurrentUser(user=user, session_id=session_id)


def require_permission(*permissions: Perm) -> Callable[..., CurrentUser]:
    """Dependency factory: the caller must hold every listed permission, otherwise 403."""

    def dependency(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not all(current.has(p) for p in permissions):
            raise ForbiddenError("You do not have permission to perform this action.")
        return current

    return dependency
