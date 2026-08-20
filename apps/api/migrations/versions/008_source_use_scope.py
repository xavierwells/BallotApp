"""Separate direct-link/manual-check permission from content-reuse approval.

Revision ID: 008_source_use_scope
Revises: 007_source_check_operations
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "008_source_use_scope"
down_revision = "007_source_check_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "authority_source_registry",
        sa.Column("permitted_use", sa.String(32), server_default="none", nullable=False),
    )
    op.add_column("authority_source_registry", sa.Column("permitted_use_reviewer_reference", sa.String(128), nullable=True))
    op.add_column("authority_source_registry", sa.Column("permitted_use_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("authority_source_registry", sa.Column("permitted_use_notes", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_authority_source_registry_permitted_use",
        "authority_source_registry",
        "permitted_use IN ('none', 'direct_link_manual_check', 'private_retention', 'public_copy')",
    )
    op.create_check_constraint(
        "ck_authority_source_registry_permitted_use_review",
        "authority_source_registry",
        "permitted_use = 'none' OR "
        "(permitted_use_reviewer_reference IS NOT NULL AND permitted_use_reviewed_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_authority_source_registry_content_use_approved",
        "authority_source_registry",
        "permitted_use NOT IN ('private_retention', 'public_copy') OR approval_status = 'approved'",
    )
    op.create_check_constraint(
        "ck_authority_source_registry_nonzero_use_active",
        "authority_source_registry",
        "permitted_use = 'none' OR approval_status IN ('pending_review', 'approved')",
    )
    op.create_index(
        "ix_authority_source_registry_permitted_use",
        "authority_source_registry",
        ["permitted_use", "next_check_at"],
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
