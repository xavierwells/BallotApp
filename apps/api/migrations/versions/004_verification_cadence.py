"""Add adjustable source verification cadence and immutable check history.

Revision ID: 004_verification_cadence
Revises: 003_doc_retention
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_verification_cadence"
down_revision = "003_doc_retention"
branch_labels = None
depends_on = None


uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "verification_cadence_policies",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("election_authority_id", uuid, sa.ForeignKey("election_authorities.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("ordinary_interval_hours", sa.SmallInteger(), server_default="720", nullable=False),
        sa.Column("active_window_days", sa.SmallInteger(), server_default="90", nullable=False),
        sa.Column("active_interval_hours", sa.SmallInteger(), server_default="168", nullable=False),
        sa.Column("official_ballot_interval_hours", sa.SmallInteger(), server_default="24", nullable=False),
        sa.Column("updated_by_reference", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "(publication_id IS NULL AND election_authority_id IS NULL) OR "
            "(publication_id IS NOT NULL AND election_authority_id IS NULL) OR "
            "(publication_id IS NULL AND election_authority_id IS NOT NULL)",
            name="ck_verification_cadence_policies_single_scope",
        ),
        sa.CheckConstraint("ordinary_interval_hours > 0", name="ck_verification_cadence_policies_ordinary_interval"),
        sa.CheckConstraint("active_window_days > 0", name="ck_verification_cadence_policies_active_window"),
        sa.CheckConstraint("active_interval_hours > 0", name="ck_verification_cadence_policies_active_interval"),
        sa.CheckConstraint("official_ballot_interval_hours > 0", name="ck_verification_cadence_policies_ballot_interval"),
    )
    op.create_index(
        "uq_verification_cadence_policies_organization",
        "verification_cadence_policies",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("publication_id IS NULL AND election_authority_id IS NULL"),
    )
    op.create_index(
        "uq_verification_cadence_policies_publication",
        "verification_cadence_policies",
        ["publication_id"],
        unique=True,
        postgresql_where=sa.text("publication_id IS NOT NULL"),
    )
    op.create_index(
        "uq_verification_cadence_policies_authority",
        "verification_cadence_policies",
        ["election_authority_id"],
        unique=True,
        postgresql_where=sa.text("election_authority_id IS NOT NULL"),
    )
    op.execute(
        """
        CREATE FUNCTION validate_verification_cadence_policy_scope() RETURNS trigger AS $$
        BEGIN
          IF NEW.publication_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM publications
            WHERE id = NEW.publication_id AND organization_id = NEW.organization_id
          ) THEN
            RAISE EXCEPTION 'publication verification policy must belong to its organization';
          END IF;
          IF NEW.election_authority_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM election_authorities
            JOIN publications ON publications.id = election_authorities.publication_id
            WHERE election_authorities.id = NEW.election_authority_id
              AND publications.organization_id = NEW.organization_id
          ) THEN
            RAISE EXCEPTION 'authority verification policy must belong to its organization';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER verification_cadence_policies_scope_valid
        BEFORE INSERT OR UPDATE ON verification_cadence_policies
        FOR EACH ROW EXECUTE FUNCTION validate_verification_cadence_policy_scope();
        """
    )

    op.add_column("elections", sa.Column("election_authority_id", uuid, nullable=True))
    op.create_foreign_key(
        "fk_elections_election_authority",
        "elections",
        "election_authorities",
        ["election_authority_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_elections_authority_date", "elections", ["election_authority_id", "election_date"])

    op.add_column("authority_source_registry", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("authority_source_registry", sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_authority_source_registry_next_check",
        "authority_source_registry",
        ["next_check_at"],
        postgresql_where=sa.text("approval_status = 'approved'"),
    )

    op.create_table(
        "source_verification_checks",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("authority_source_registry_id", uuid, sa.ForeignKey("authority_source_registry.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_id", uuid, sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.String(24), nullable=False),
        sa.Column("checker_reference", sa.String(128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "result IN ('unchanged', 'changed', 'unavailable', 'terms_changed')",
            name="ck_source_verification_checks_result",
        ),
    )
    op.create_index("ix_source_verification_checks_source_time", "source_verification_checks", ["authority_source_registry_id", "checked_at"])
    op.create_index("ix_source_verification_checks_next_check", "source_verification_checks", ["next_check_at"])

    op.execute(
        """
        CREATE FUNCTION prevent_source_verification_check_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'source verification checks are immutable';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER source_verification_checks_immutable
        BEFORE UPDATE OR DELETE ON source_verification_checks
        FOR EACH ROW EXECUTE FUNCTION prevent_source_verification_check_mutation();
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
