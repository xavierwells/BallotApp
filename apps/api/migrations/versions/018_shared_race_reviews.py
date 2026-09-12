"""Preserve the exact review evidence used by a private county import.

Revision ID: 018_shared_race_reviews
Revises: 017_editorial_corrections
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018_shared_race_reviews"
down_revision = "017_editorial_corrections"
branch_labels = depends_on = None


def upgrade() -> None:
    # Existing promotions and decisions remain untouched. New receipts are part
    # of the already append-only promotion row, not fabricated county reviews.
    op.add_column("editorial_promotions", sa.Column("review_snapshot", postgresql.JSONB()))


def downgrade() -> None:
    raise NotImplementedError("Provenance migrations are forward-only; restore a verified backup.")
