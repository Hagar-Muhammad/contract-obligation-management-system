"""obligations: obligations with recurrence and overdue tracking; evidence on contract documents (FR-OBL-*)

Revision ID: 0007_obligations
Revises: 0006_documents
Create Date: 2026-10-23 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0007_obligations'
down_revision: str | None = '0006_documents'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('obligations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('responsible_party_id', sa.Uuid(), nullable=False),
    sa.Column('responsible_user_id', sa.Uuid(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('due_date', sa.Date(), nullable=True),
    sa.Column('priority', sa.String(length=10), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('recurrence_rule', sa.String(length=500), nullable=True),
    sa.Column('series_id', sa.Uuid(), nullable=True),
    sa.Column('penalty_text', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('overdue_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by_id', sa.Uuid(), nullable=True),
    sa.Column('updated_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name=op.f('ck_obligations_priority')),
    sa.CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'cancelled')", name=op.f('ck_obligations_status')),
    sa.CheckConstraint('recurrence_rule IS NULL OR due_date IS NOT NULL', name=op.f('ck_obligations_recurring_has_due_date')),
    sa.CheckConstraint('start_date IS NULL OR due_date IS NULL OR due_date >= start_date', name=op.f('ck_obligations_due_not_before_start')),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name=op.f('fk_obligations_contract_id_contracts'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_obligations_created_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['responsible_party_id'], ['parties.id'], name=op.f('fk_obligations_responsible_party_id_parties'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['responsible_user_id'], ['users.id'], name=op.f('fk_obligations_responsible_user_id_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_obligations_updated_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_obligations'))
    )
    op.create_index(op.f('ix_obligations_contract_id'), 'obligations', ['contract_id'], unique=False)
    op.create_index(op.f('ix_obligations_responsible_party_id'), 'obligations', ['responsible_party_id'], unique=False)
    op.create_index('ix_obligations_responsible_user_status', 'obligations', ['responsible_user_id', 'status'], unique=False)
    op.create_index(op.f('ix_obligations_series_id'), 'obligations', ['series_id'], unique=False)
    op.create_index('ix_obligations_status_due_date', 'obligations', ['status', 'due_date'], unique=False)
    op.add_column('contract_documents', sa.Column('obligation_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_contract_documents_obligation_id'), 'contract_documents', ['obligation_id'], unique=False)
    op.create_foreign_key(op.f('fk_contract_documents_obligation_id_obligations'), 'contract_documents', 'obligations', ['obligation_id'], ['id'], ondelete='RESTRICT')
    # Evidence documents (SRS 7.3): a new kind, always tied to an obligation.
    op.drop_constraint(op.f("ck_contract_documents_kind"), "contract_documents", type_="check")
    op.create_check_constraint(op.f("ck_contract_documents_kind"), "contract_documents", "kind IN ('contract', 'amendment', 'annex', 'evidence', 'other')")
    op.create_check_constraint(
        op.f("ck_contract_documents_evidence_has_obligation"),
        "contract_documents",
        "(kind = 'evidence') = (obligation_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_contract_documents_evidence_has_obligation"), "contract_documents", type_="check")
    op.drop_constraint(op.f("ck_contract_documents_kind"), "contract_documents", type_="check")
    op.create_check_constraint(op.f("ck_contract_documents_kind"), "contract_documents", "kind IN ('contract', 'amendment', 'annex', 'other')")
    op.drop_constraint(op.f('fk_contract_documents_obligation_id_obligations'), 'contract_documents', type_='foreignkey')
    op.drop_index(op.f('ix_contract_documents_obligation_id'), table_name='contract_documents')
    op.drop_column('contract_documents', 'obligation_id')
    op.drop_index('ix_obligations_status_due_date', table_name='obligations')
    op.drop_index(op.f('ix_obligations_series_id'), table_name='obligations')
    op.drop_index('ix_obligations_responsible_user_status', table_name='obligations')
    op.drop_index(op.f('ix_obligations_responsible_party_id'), table_name='obligations')
    op.drop_index(op.f('ix_obligations_contract_id'), table_name='obligations')
    op.drop_table('obligations')
