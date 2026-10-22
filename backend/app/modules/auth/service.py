"""Login, token refresh and logout (FR-AUTH-01, FR-AUTH-04, FR-USER-03)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    password_needs_rehash,
    verify_password,
)
from app.modules.auth.models import RefreshToken, UserSession
from app.modules.users.models import User

INVALID_CREDENTIALS = "Invalid email or password."


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str
    user: User


def _now() -> datetime:
    return datetime.now(UTC)


def authenticate(db: Session, email: str, password: str) -> User:
    """Return the user for valid credentials. Unknown e-mail, wrong password and inactive account all look alike."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not verify_password(password, user.password_hash if user else None) or user is None:
        raise UnauthorizedError(INVALID_CREDENTIALS)
    if not user.is_active:
        raise UnauthorizedError(INVALID_CREDENTIALS)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


def _issue_refresh_token(db: Session, session: UserSession) -> str:
    raw = new_refresh_token()
    db.add(
        RefreshToken(session_id=session.id, token_hash=hash_refresh_token(raw), expires_at=session.expires_at)
    )
    return raw


def login(
    db: Session, email: str, password: str, *, user_agent: str | None, ip_address: str | None
) -> IssuedTokens:
    user = authenticate(db, email, password)
    settings = get_settings()
    session = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        expires_at=_now() + timedelta(days=settings.refresh_token_ttl_days),
        user_agent=(user_agent or "")[:300] or None,
        ip_address=ip_address,
    )
    db.add(session)
    user.last_login_at = _now()
    refresh = _issue_refresh_token(db, session)
    access, expires_in = create_access_token(user.id, session.id)
    db.commit()
    return IssuedTokens(access, expires_in, refresh, user)


def refresh(db: Session, raw_refresh_token: str | None) -> IssuedTokens:
    """Exchange a refresh token for new tokens, rotating it. Re-use of a spent token ends the session."""
    if not raw_refresh_token:
        raise UnauthorizedError("No refresh token.")
    token = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_refresh_token))
    )
    if token is None:
        raise UnauthorizedError("Invalid refresh token.")
    session = db.get(UserSession, token.session_id)
    if session is None or session.revoked_at is not None:
        raise UnauthorizedError("Session has ended. Please log in again.")
    if token.used_at is not None:
        # A rotated token came back: it was probably stolen. Kill the session for everyone holding it.
        session.revoked_at = _now()
        db.commit()
        raise UnauthorizedError("Session has ended. Please log in again.")
    if token.expires_at <= _now() or session.expires_at <= _now():
        raise UnauthorizedError("Session has expired. Please log in again.")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is not active.")

    token.used_at = _now()
    new_refresh = _issue_refresh_token(db, session)
    access, expires_in = create_access_token(user.id, session.id)
    db.commit()
    return IssuedTokens(access, expires_in, new_refresh, user)


def logout(db: Session, *, session_id: uuid.UUID | None, raw_refresh_token: str | None) -> None:
    """End the session identified by the access token and/or the refresh cookie. Idempotent."""
    ids: set[uuid.UUID] = set()
    if session_id is not None:
        ids.add(session_id)
    if raw_refresh_token:
        token = db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_refresh_token))
        )
        if token is not None:
            ids.add(token.session_id)
    if ids:
        db.execute(
            update(UserSession)
            .where(UserSession.id.in_(ids), UserSession.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        db.commit()


def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> None:
    """Used when an account is deactivated or its password is reset. Caller commits."""
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
