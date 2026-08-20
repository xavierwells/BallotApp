"""Track private document retention and public visibility separately.

Revision ID: 003_document_retention_visibility
Revises: 002_authority_source_registry
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "003_document_retention_visibility"
down_revision = "002_authority_source_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("artifact_retention", sa.String(24), server_default="retained", nullable=False),
    )
    op.add_column(
        "documents",
        sa.Column("public_access_level", sa.String(24), server_default="metadata_only", nullable=False),
    )
    op.add_column("documents", sa.Column("content_length_bytes", sa.BigInteger(), nullable=True))
    op.create_check_constraint(
        "ck_documents_artifact_retention",
        "documents",
        "artifact_retention = 'retained'",
    )
    op.create_check_constraint(
        "ck_documents_public_access_level",
        "documents",
        "public_access_level IN ('metadata_only', 'public_copy')",
    )
    op.create_check_constraint(
        "ck_documents_content_length",
        "documents",
        "content_length_bytes IS NULL OR content_length_bytes >= 0",
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
