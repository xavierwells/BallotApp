"""Add stable race keys and ballot publication completeness gates.

Revision ID: 013_official_ballot_intake
Revises: 012_browse_area_coverage
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "013_official_ballot_intake"
down_revision = "012_browse_area_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("races", sa.Column("external_identifier", sa.String(255), nullable=True))
    op.create_index(
        "uq_races_external_identifier",
        "races",
        ["publication_id", "election_id", "external_identifier"],
        unique=True,
        postgresql_where=sa.text("external_identifier IS NOT NULL"),
    )
    op.execute(
        """
        CREATE FUNCTION protect_final_ballot_items() RETURNS trigger AS $$
        DECLARE ballot_status ballot_publication_status;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            SELECT status INTO ballot_status FROM ballot_versions WHERE id = OLD.ballot_version_id;
          ELSE
            SELECT status INTO ballot_status FROM ballot_versions WHERE id = NEW.ballot_version_id;
          END IF;
          IF ballot_status IN ('published', 'superseded', 'archived') THEN
            RAISE EXCEPTION 'published ballot items are immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ballot_items_final_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON ballot_items
        FOR EACH ROW EXECUTE FUNCTION protect_final_ballot_items();

        CREATE FUNCTION require_complete_ballot_before_publication() RETURNS trigger AS $$
        DECLARE reviewer_count integer;
        BEGIN
          IF NEW.status = 'published' AND OLD.status <> 'published' THEN
            IF NOT EXISTS (SELECT 1 FROM ballot_items WHERE ballot_version_id = NEW.id) THEN
              RAISE EXCEPTION 'a ballot must have items before publication';
            END IF;
            IF EXISTS (
              SELECT 1 FROM ballot_items
              WHERE ballot_version_id = NEW.id AND NULLIF(BTRIM(source_page), '') IS NULL
            ) THEN
              RAISE EXCEPTION 'every ballot item requires an official-document page citation';
            END IF;
            SELECT COUNT(DISTINCT actor_reference) INTO reviewer_count
            FROM verification_events
            WHERE target_type = 'ballot_version' AND target_id = NEW.id
              AND action = 'verified' AND actor_role = 'verifier';
            IF reviewer_count < 2 THEN
              RAISE EXCEPTION 'a ballot requires verification by two distinct reviewers before publication';
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ballot_versions_require_complete_content
        BEFORE UPDATE OF status ON ballot_versions
        FOR EACH ROW EXECUTE FUNCTION require_complete_ballot_before_publication();
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
