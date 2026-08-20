"""Classify source monitoring and require explicit automation approval.

Revision ID: 005_source_monitoring
Revises: 004_verification_cadence
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "005_source_monitoring"
down_revision = "004_verification_cadence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "authority_source_registry",
        sa.Column("monitoring_class", sa.String(24), server_default="reference", nullable=False),
    )
    op.add_column(
        "authority_source_registry",
        sa.Column("automated_monitoring_allowed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_check_constraint(
        "ck_authority_source_registry_monitoring_class",
        "authority_source_registry",
        "monitoring_class IN ('active_ballot', 'active_election', 'reference', 'disabled')",
    )
    op.create_check_constraint(
        "ck_authority_source_registry_automation_approved",
        "authority_source_registry",
        "NOT automated_monitoring_allowed OR approval_status = 'approved'",
    )
    op.create_index(
        "ix_authority_source_registry_monitoring",
        "authority_source_registry",
        ["approval_status", "monitoring_class", "next_check_at"],
    )

    op.add_column(
        "source_verification_checks",
        sa.Column("check_method", sa.String(16), server_default="manual", nullable=False),
    )
    op.create_check_constraint(
        "ck_source_verification_checks_method",
        "source_verification_checks",
        "check_method IN ('manual', 'automated')",
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
