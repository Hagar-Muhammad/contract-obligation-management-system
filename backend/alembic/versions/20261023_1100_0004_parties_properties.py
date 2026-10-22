"""parties and properties: party directory, property register, property assignments (FR-PARTY-01/02, SRS 4.6)

Revision ID: 0004_parties_properties
Revises: 0003_audit_logs
Create Date: 2026-10-23 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0004_parties_properties'
down_revision: str | None = '0003_audit_logs'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('parties',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('party_type', sa.String(length=20), nullable=False),
    sa.Column('display_name', sa.String(length=300), nullable=False),
    sa.Column('national_id', sa.String(length=50), nullable=True),
    sa.Column('passport_no', sa.String(length=50), nullable=True),
    sa.Column('registration_no', sa.String(length=50), nullable=True),
    sa.Column('tax_no', sa.String(length=50), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.Uuid(), nullable=True),
    sa.Column('updated_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("party_type = 'individual' OR (national_id IS NULL AND passport_no IS NULL)", name=op.f('ck_parties_organization_has_no_personal_ids')),
    sa.CheckConstraint("party_type = 'organization' OR (registration_no IS NULL AND tax_no IS NULL)", name=op.f('ck_parties_individual_has_no_company_ids')),
    sa.CheckConstraint("party_type IN ('individual', 'organization')", name=op.f('ck_parties_party_type')),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_parties_created_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_parties_updated_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_parties'))
    )
    op.create_index(op.f('ix_parties_display_name'), 'parties', ['display_name'], unique=False)
    op.create_index('uq_parties_national_id', 'parties', ['national_id'], unique=True, postgresql_where=sa.text('national_id IS NOT NULL'))
    op.create_index('uq_parties_passport_no', 'parties', ['passport_no'], unique=True, postgresql_where=sa.text('passport_no IS NOT NULL'))
    op.create_index('uq_parties_registration_no', 'parties', ['registration_no'], unique=True, postgresql_where=sa.text('registration_no IS NOT NULL'))
    op.create_table('properties',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('property_type', sa.String(length=30), nullable=False),
    sa.Column('address', sa.Text(), nullable=True),
    sa.Column('city', sa.String(length=100), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('area_sqm', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_by_id', sa.Uuid(), nullable=True),
    sa.Column('updated_by_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("property_type IN ('residential', 'retail', 'office', 'industrial', 'land', 'mixed_use', 'other')", name=op.f('ck_properties_property_type')),
    sa.CheckConstraint('area_sqm IS NULL OR area_sqm > 0', name=op.f('ck_properties_area_positive')),
    sa.CheckConstraint('code = upper(code)', name=op.f('ck_properties_code_uppercase')),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_properties_created_by_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_properties_updated_by_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_properties')),
    sa.UniqueConstraint('code', name=op.f('uq_properties_code'))
    )
    op.create_index(op.f('ix_properties_name'), 'properties', ['name'], unique=False)
    op.create_table('property_assignments',
    sa.Column('property_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['property_id'], ['properties.id'], name=op.f('fk_property_assignments_property_id_properties'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_property_assignments_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('property_id', 'user_id', name=op.f('pk_property_assignments'))
    )
    op.create_index(op.f('ix_property_assignments_user_id'), 'property_assignments', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_property_assignments_user_id'), table_name='property_assignments')
    op.drop_table('property_assignments')
    op.drop_index(op.f('ix_properties_name'), table_name='properties')
    op.drop_table('properties')
    op.drop_index('uq_parties_registration_no', table_name='parties', postgresql_where=sa.text('registration_no IS NOT NULL'))
    op.drop_index('uq_parties_passport_no', table_name='parties', postgresql_where=sa.text('passport_no IS NOT NULL'))
    op.drop_index('uq_parties_national_id', table_name='parties', postgresql_where=sa.text('national_id IS NOT NULL'))
    op.drop_index(op.f('ix_parties_display_name'), table_name='parties')
    op.drop_table('parties')
