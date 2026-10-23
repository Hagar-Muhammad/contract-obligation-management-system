"""search: search_normalize() for case-, diacritic- and letter-form-insensitive search (FR-SEARCH-01, D-16)

Revision ID: 0008_search
Revises: 0007_obligations
Create Date: 2026-10-23 15:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008_search"
down_revision: str | None = "0007_obligations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mirrors app/core/search.py normalize(): drop Arabic diacritics and tatweel, unify alef forms, ta marbuta → ha,
# alef maqsura → ya, lower-case. IMMUTABLE so it can be used in expression indexes later.
NORMALIZE = r"""
CREATE FUNCTION search_normalize(value text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE RETURNS NULL ON NULL INPUT AS $$
    SELECT lower(translate(
        regexp_replace(value, '[\u064B-\u0652\u0670\u0640]', '', 'g'),
        'أإآٱةى',
        'ااااهي'
    ))
$$
"""


def upgrade() -> None:
    op.execute(NORMALIZE)


def downgrade() -> None:
    op.execute("DROP FUNCTION search_normalize(text)")
