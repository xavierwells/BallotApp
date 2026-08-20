"""Add election authorities and the external-source approval registry.

Revision ID: 002_authority_source_registry
Revises: 001_provenance_core
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002_authority_source_registry"
down_revision = "001_provenance_core"
branch_labels = None
depends_on = None


uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "election_authorities",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("authority_type", sa.String(40), nullable=False),
        sa.Column("official_website_url", sa.String(2048), nullable=False),
        sa.Column("status", sa.String(24), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("publication_id", "slug", name="uq_election_authorities_publication_slug"),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_election_authorities_slug"),
        sa.CheckConstraint(
            "authority_type IN ('municipality', 'county', 'school_district', 'state', 'special_district', 'other')",
            name="ck_election_authorities_type",
        ),
        sa.CheckConstraint("status IN ('draft', 'active', 'retired')", name="ck_election_authorities_status"),
    )
    op.create_index("ix_election_authorities_publication_status", "election_authorities", ["publication_id", "status"])

    op.create_table(
        "authority_source_registry",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("authority_id", uuid, sa.ForeignKey("election_authorities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("source_category", sa.String(40), nullable=False),
        sa.Column("terms_url", sa.String(2048), nullable=True),
        sa.Column("source_license", sa.String(255), nullable=True),
        sa.Column("cost_model", sa.String(255), nullable=True),
        sa.Column("rate_limit", sa.String(255), nullable=True),
        sa.Column("retention_rule", sa.Text(), nullable=True),
        sa.Column("attribution_requirement", sa.Text(), nullable=True),
        sa.Column("redistribution_rights", sa.Text(), nullable=True),
        sa.Column("approval_status", sa.String(24), server_default="pending_review", nullable=False),
        sa.Column("reviewer_reference", sa.String(128), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("authority_id", "slug", name="uq_authority_source_registry_authority_slug"),
        sa.UniqueConstraint("id", "authority_id", name="uq_authority_source_registry_id_authority"),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_authority_source_registry_slug"),
        sa.CheckConstraint(
            "source_category IN ('election_information', 'notices', 'ballots', 'results', 'candidate_filings', 'boundaries', 'other')",
            name="ck_authority_source_registry_category",
        ),
        sa.CheckConstraint(
            "approval_status IN ('pending_review', 'approved', 'rejected', 'retired')",
            name="ck_authority_source_registry_approval_status",
        ),
        sa.CheckConstraint(
            "approval_status <> 'approved' OR "
            "(terms_url IS NOT NULL AND source_license IS NOT NULL AND cost_model IS NOT NULL "
            "AND rate_limit IS NOT NULL AND retention_rule IS NOT NULL "
            "AND attribution_requirement IS NOT NULL AND redistribution_rights IS NOT NULL "
            "AND reviewer_reference IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_authority_source_registry_approved_reviewed",
        ),
    )
    op.create_index(
        "ix_authority_source_registry_authority_status",
        "authority_source_registry",
        ["authority_id", "approval_status"],
    )
    op.create_index(
        "ix_authority_source_registry_next_review",
        "authority_source_registry",
        ["next_review_at"],
        postgresql_where=sa.text("approval_status = 'approved'"),
    )

    op.add_column("documents", sa.Column("election_authority_id", uuid, nullable=True))
    op.add_column("documents", sa.Column("authority_source_registry_id", uuid, nullable=True))
    op.create_foreign_key(
        "fk_documents_election_authority",
        "documents",
        "election_authorities",
        ["election_authority_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_documents_registry_authority",
        "documents",
        "authority_source_registry",
        ["authority_source_registry_id", "election_authority_id"],
        ["id", "authority_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_documents_registry_requires_authority",
        "documents",
        "authority_source_registry_id IS NULL OR election_authority_id IS NOT NULL",
    )
    op.create_index("ix_documents_election_authority", "documents", ["election_authority_id"])


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
