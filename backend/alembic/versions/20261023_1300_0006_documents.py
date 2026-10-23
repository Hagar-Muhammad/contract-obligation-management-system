"""documents: contract_documents, write-once originals with SHA-256 (FR-DOC-01..05, BR-09)

Revision ID: 0006_documents
Revises: 0005_contracts
Create Date: 2026-10-23 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0006_documents'
down_revision: str | None = '0005_contracts'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('contract_documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('file_type', sa.String(length=10), nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_key', sa.String(length=500), nullable=False),
    sa.Column('uploaded_by_id', sa.Uuid(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('contract', 'amendment', 'annex', 'other')", name=op.f('ck_contract_documents_kind')),
    sa.CheckConstraint('size_bytes > 0', name=op.f('ck_contract_documents_size_positive')),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name=op.f('fk_contract_documents_contract_id_contracts'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], name=op.f('fk_contract_documents_uploaded_by_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contract_documents')),
    sa.UniqueConstraint('storage_key', name=op.f('uq_contract_documents_storage_key'))
    )
    op.create_index(op.f('ix_contract_documents_contract_id'), 'contract_documents', ['contract_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_contract_documents_contract_id'), table_name='contract_documents')
    op.drop_table('contract_documents')
