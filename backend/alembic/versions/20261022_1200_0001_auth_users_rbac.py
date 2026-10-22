"""auth, users and RBAC: users, roles, permissions, sessions, refresh tokens + seed of SRS 2.3 / 3.2

Revision ID: 0001_auth_users_rbac
Revises:
Create Date: 2026-10-22 12:00:00
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_auth_users_rbac"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen copy of app/modules/users/rbac.py at the time of this migration. Later changes go in new migrations;
# tests/test_rbac.py checks the database still matches the catalog.
PERMISSIONS = {
    "contract:view": "View contracts",
    "contract:create": "Create contracts",
    "contract:edit": "Edit contracts",
    "contract:archive": "Archive and restore contracts",
    "document:view": "View and download contract documents",
    "document:upload": "Upload contract documents",
    "extraction:run": "Start extraction on a document",
    "extraction:confirm": "Review and confirm extracted data",
    "obligation:view": "View obligations",
    "obligation:create": "Create obligations",
    "obligation:update": "Update obligations and their status",
    "party:manage": "Create and update parties",
    "property:manage": "Create and update properties and assignments",
    "report:view": "View dashboards and reports",
    "report:export": "Export report data",
    "user:manage": "Manage user accounts and their roles",
    "role:manage": "Change role permissions",
    "audit:view": "Read the audit log",
}

_CORE = ["contract:view", "document:view", "obligation:view", "report:view"]
ROLES = {
    "admin": (
        "Administrator",
        "Manage users, roles, permissions, and system settings.",
        "all",
        list(PERMISSIONS),
    ),
    "contract_manager": (
        "Contract Manager",
        "Manage contracts, parties, documents, and obligations.",
        "all",
        [*_CORE, "contract:create", "contract:edit", "contract:archive", "document:upload", "extraction:run",
         "extraction:confirm", "obligation:create", "obligation:update", "party:manage", "property:manage",
         "report:export"],
    ),
    "legal": (
        "Legal User",
        "Review contract information, extracted data, and obligations.",
        "all",
        [*_CORE, "contract:create", "contract:edit", "contract:archive", "document:upload", "extraction:run",
         "extraction:confirm", "obligation:create", "obligation:update", "party:manage", "report:export"],
    ),
    "property_manager": (
        "Property Manager",
        "Manage contracts and obligations related to assigned properties.",
        "assigned_properties",
        [*_CORE, "contract:create", "contract:edit", "contract:archive", "document:upload", "extraction:run",
         "extraction:confirm", "obligation:create", "obligation:update", "party:manage"],
    ),
    "employee": (
        "Employee / Responsible User",
        "View and complete assigned obligations and update status.",
        "assigned_obligations",
        [*_CORE, "document:upload", "extraction:run", "obligation:create", "obligation:update"],
    ),
    "management": (
        "Management",
        "View dashboards, reports, contract status, and obligation summaries.",
        "all",
        [*_CORE, "report:export"],
    ),
}  # fmt: skip


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("code", name=op.f("uq_permissions_code")),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("data_scope", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
        sa.CheckConstraint(
            "data_scope IN ('all', 'assigned_properties', 'assigned_obligations')", name=op.f("ck_roles_data_scope")
        ),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("preferred_language", sa.String(5), server_default="en", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], name=op.f("fk_users_created_by_id_users"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"], ["users.id"], name=op.f("fk_users_updated_by_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_email_lowercase")),
        sa.CheckConstraint("preferred_language IN ('en', 'ar')", name=op.f("ck_users_preferred_language")),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name=op.f("fk_role_permissions_permission_id_permissions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name=op.f("fk_role_permissions_role_id_roles"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name=op.f("pk_role_permissions")),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name=op.f("fk_user_roles_role_id_roles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_roles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_user_roles")),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"])
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["user_sessions.id"],
            name=op.f("fk_refresh_tokens_session_id_user_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_session_id"), "refresh_tokens", ["session_id"])

    _seed()


def _seed() -> None:
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String()), sa.column("description", sa.String())
    )
    roles = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("data_scope", sa.String()),
    )
    role_permissions = sa.table("role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid()))

    perm_ids = {code: uuid.uuid4() for code in PERMISSIONS}
    op.bulk_insert(
        permissions, [{"id": perm_ids[c], "code": c, "description": d} for c, d in PERMISSIONS.items()]
    )
    role_rows, links = [], []
    for code, (name, description, scope, perms) in ROLES.items():
        role_id = uuid.uuid4()
        role_rows.append({"id": role_id, "code": code, "name": name, "description": description, "data_scope": scope})
        links += [{"role_id": role_id, "permission_id": perm_ids[p]} for p in perms]
    op.bulk_insert(roles, role_rows)
    op.bulk_insert(role_permissions, links)


def downgrade() -> None:
    op.drop_index(op.f("ix_refresh_tokens_session_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("permissions")
