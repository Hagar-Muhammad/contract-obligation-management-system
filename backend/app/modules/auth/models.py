import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.models import uuid_pk


class UserSession(Base):
    """One login. Access tokens carry the session id, so revoking the session ends it at once (FR-AUTH-04)."""

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # "Keep me signed in": a remembered session gets a persistent cookie; otherwise the cookie ends with the browser.
    remember: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip_address: Mapped[str | None] = mapped_column(String(45))


class RefreshToken(Base):
    """Single-use refresh token. Presenting one that was already used revokes the whole session."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_sessions.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_session: Mapped[UserSession] = relationship()
