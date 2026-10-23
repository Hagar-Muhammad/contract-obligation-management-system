"""contracts: types, statuses (seeded), contracts, contract parties and properties (FR-CON-*, FR-PARTY-03, FR-PROP-01)

Revision ID: 0005_contracts
Revises: 0004_parties_properties
Create Date: 2026-10-23 12:00:00
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0005_contracts'
down_revision: str | None = '0004_parties_properties'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('contract_statuses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name_en', sa.String(length=100), nullable=False),
    sa.Column('name_ar', sa.String(length=100), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contract_statuses')),
    sa.UniqueConstraint('code', name=op.f('uq_contract_statuses_code'))
    )
    op.create_table('contract_types',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name_en', sa.String(length=100), nullable=False),
    sa.Column('name_ar', sa.String(length=100), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contract_types')),
    sa.UniqueConstraint('code', name=op.f('uq_contract_types_code'))
    )
    op.create_table('contracts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('contract_number', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('contract_type_id', sa.Uuid(), nullable=False),
    sa.Column('status_id', sa.Uuid(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('value_amount', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('renewal_date', sa.Date(), nullable=True),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('archived_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_by_id', sa.Uuid(), nullable=True),
    sa.Column('updated_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(value_amount IS NULL) = (currency IS NULL)', name=op.f('ck_contracts_value_has_currency')),
    sa.CheckConstraint('contract_number = upper(contract_number)', name=op.f('ck_contracts_number_uppercase')),
    sa.CheckConstraint('end_date IS NULL OR end_date >= start_date', name=op.f('ck_contracts_end_not_before_start')),
    sa.CheckConstraint('value_amount IS NULL OR value_amount >= 0', name=op.f('ck_contracts_value_not_negative')),
    sa.ForeignKeyConstraint(['archived_by_id'], ['users.id'], name=op.f('fk_contracts_archived_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['contract_type_id'], ['contract_types.id'], name=op.f('fk_contracts_contract_type_id_contract_types')),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_contracts_created_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['status_id'], ['contract_statuses.id'], name=op.f('fk_contracts_status_id_contract_statuses')),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_contracts_updated_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contracts')),
    sa.UniqueConstraint('contract_number', name=op.f('uq_contracts_contract_number'))
    )
    op.create_index(op.f('ix_contracts_archived_at'), 'contracts', ['archived_at'], unique=False)
    op.create_index(op.f('ix_contracts_contract_type_id'), 'contracts', ['contract_type_id'], unique=False)
    op.create_index(op.f('ix_contracts_end_date'), 'contracts', ['end_date'], unique=False)
    op.create_index(op.f('ix_contracts_status_id'), 'contracts', ['status_id'], unique=False)
    op.create_table('contract_parties',
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('party_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name=op.f('fk_contract_parties_contract_id_contracts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['party_id'], ['parties.id'], name=op.f('fk_contract_parties_party_id_parties'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('contract_id', 'party_id', name=op.f('pk_contract_parties'))
    )
    op.create_index(op.f('ix_contract_parties_party_id'), 'contract_parties', ['party_id'], unique=False)
    op.create_table('contract_properties',
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('property_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], name=op.f('fk_contract_properties_contract_id_contracts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name=op.f('fk_contract_properties_property_id_properties'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('contract_id', 'property_id', name=op.f('pk_contract_properties'))
    )
    op.create_index(op.f('ix_contract_properties_property_id'), 'contract_properties', ['property_id'], unique=False)
    _seed()


def downgrade() -> None:
    op.drop_index(op.f('ix_contract_properties_property_id'), table_name='contract_properties')
    op.drop_table('contract_properties')
    op.drop_index(op.f('ix_contract_parties_party_id'), table_name='contract_parties')
    op.drop_table('contract_parties')
    op.drop_index(op.f('ix_contracts_status_id'), table_name='contracts')
    op.drop_index(op.f('ix_contracts_end_date'), table_name='contracts')
    op.drop_index(op.f('ix_contracts_contract_type_id'), table_name='contracts')
    op.drop_index(op.f('ix_contracts_archived_at'), table_name='contracts')
    op.drop_table('contracts')
    op.drop_table('contract_types')
    op.drop_table('contract_statuses')


# SRS 4.4 (decision D-03) and decision D-17. Frozen here; later changes go in new migrations or are made as data.
CONTRACT_TYPES = [
    ("lease", "Lease", "إيجار"),
    ("sale_purchase", "Sale / Purchase", "بيع / شراء"),
    ("service_maintenance", "Service / Maintenance", "خدمات / صيانة"),
    ("construction", "Construction", "مقاولات"),
    ("consulting", "Consulting", "استشارات"),
    ("marketing", "Marketing", "تسويق"),
    ("partnership", "Partnership / Joint Venture", "شراكة / مشروع مشترك"),
    ("nda", "NDA", "اتفاقية عدم إفصاح"),
    ("license", "License", "ترخيص"),
    ("other", "Other", "أخرى"),
]
CONTRACT_STATUSES = [
    ("draft", "Draft", "مسودة"),
    ("active", "Active", "سارٍ"),
    ("expired", "Expired", "منتهٍ"),
    ("terminated", "Terminated", "مفسوخ"),
    ("cancelled", "Cancelled", "ملغى"),
]


def _seed() -> None:
    for table_name, rows in (("contract_types", CONTRACT_TYPES), ("contract_statuses", CONTRACT_STATUSES)):
        table = sa.table(
            table_name,
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
            sa.column("name_en", sa.String()),
            sa.column("name_ar", sa.String()),
            sa.column("sort_order", sa.Integer()),
        )
        op.bulk_insert(
            table,
            [
                {"id": uuid.uuid4(), "code": code, "name_en": en, "name_ar": ar, "sort_order": i * 10}
                for i, (code, en, ar) in enumerate(rows, start=1)
            ],
        )
