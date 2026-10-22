"""user_sessions.remember for "Keep me signed in on this device"

Revision ID: 0002_session_remember
Revises: 0001_auth_users_rbac
Create Date: 2026-10-22 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_session_remember"
down_revision: str | None = "0001_auth_users_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_sessions", sa.Column("remember", sa.Boolean(), server_default="true", nullable=False))


def downgrade() -> None:
    op.drop_column("user_sessions", "remember")
