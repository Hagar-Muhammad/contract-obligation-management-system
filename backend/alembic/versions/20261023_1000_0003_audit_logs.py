"""audit trail: append-only audit_logs (FR-AUD-01..03)

Revision ID: 0003_audit_logs
Revises: 0002_session_remember
Create Date: 2026-10-23 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_audit_logs"
down_revision: str | None = "0002_session_remember"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False
        ),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("target_label", sa.String(length=300), nullable=True),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f("fk_audit_logs_actor_user_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
        sa.CheckConstraint("actor_type IN ('user', 'system', 'anonymous')", name=op.f("ck_audit_logs_actor_type")),
        sa.CheckConstraint(
            "(actor_type = 'user') = (actor_user_id IS NOT NULL)",
            name=op.f("ck_audit_logs_actor_user_matches_type"),
        ),
    )
    op.create_index(op.f("ix_audit_logs_occurred_at"), "audit_logs", ["occurred_at"])
    op.create_index(op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"])
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_type", "target_id"])

    # FR-AUD-03: records cannot be changed or removed, whatever the application (or a bug in it) asks for.
    op.execute(
        """
        CREATE FUNCTION audit_logs_block_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER audit_logs_no_update_delete BEFORE UPDATE OR DELETE ON audit_logs "
        "FOR EACH ROW EXECUTE FUNCTION audit_logs_block_change()"
    )
    op.execute(
        "CREATE TRIGGER audit_logs_no_truncate BEFORE TRUNCATE ON audit_logs "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit_logs_block_change()"
    )


def downgrade() -> None:
    op.drop_table("audit_logs")  # drops its triggers too
    op.execute("DROP FUNCTION audit_logs_block_change()")
