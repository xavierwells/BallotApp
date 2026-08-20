"""Map ballot versions to verified combinations of geographic areas.

Revision ID: 011_ballot_area_requirements
Revises: 010_boundary_source_roles
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "011_ballot_area_requirements"
down_revision = "010_boundary_source_roles"
branch_labels = None
depends_on = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_ballot_versions_id_publication",
        "ballot_versions",
        ["id", "publication_id"],
    )
    op.create_unique_constraint(
        "uq_election_authorities_id_publication",
        "election_authorities",
        ["id", "publication_id"],
    )
    op.create_unique_constraint(
        "uq_documents_id_publication",
        "documents",
        ["id", "publication_id"],
    )
    op.create_table(
        "ballot_geographic_requirements",
        sa.Column("ballot_version_id", uuid, nullable=False),
        sa.Column("publication_id", uuid, nullable=False),
        sa.Column("geographic_area_id", uuid, nullable=False),
        sa.Column("authority_id", uuid, nullable=False),
        sa.Column("source_document_id", uuid, nullable=False),
        sa.Column("verified_by_reference", sa.String(128), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ballot_version_id", "publication_id"],
            ["ballot_versions.id", "ballot_versions.publication_id"],
            name="fk_ballot_area_requirements_ballot_publication",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id", "publication_id"],
            ["documents.id", "documents.publication_id"],
            name="fk_ballot_area_requirements_document_publication",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["geographic_area_id", "authority_id"],
            ["geographic_areas.id", "geographic_areas.authority_id"],
            name="fk_ballot_area_requirements_area_authority",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["authority_id", "publication_id"],
            ["election_authorities.id", "election_authorities.publication_id"],
            name="fk_ballot_area_requirements_authority_publication",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "ballot_version_id",
            "geographic_area_id",
            name="pk_ballot_geographic_requirements",
        ),
    )
    op.create_index(
        "ix_ballot_area_requirements_area",
        "ballot_geographic_requirements",
        ["geographic_area_id", "ballot_version_id"],
    )
    op.execute(
        """
        CREATE FUNCTION protect_final_ballot_area_requirements() RETURNS trigger AS $$
        DECLARE
          old_status ballot_publication_status;
          new_status ballot_publication_status;
        BEGIN
          IF TG_OP IN ('UPDATE', 'DELETE') THEN
            SELECT status INTO old_status FROM ballot_versions WHERE id = OLD.ballot_version_id;
          END IF;
          IF TG_OP IN ('INSERT', 'UPDATE') THEN
            SELECT status INTO new_status FROM ballot_versions WHERE id = NEW.ballot_version_id;
          END IF;
          IF old_status IN ('published', 'superseded', 'archived')
             OR new_status IN ('published', 'superseded', 'archived') THEN
            RAISE EXCEPTION 'published ballot geographic requirements are immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ballot_area_requirements_final_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON ballot_geographic_requirements
        FOR EACH ROW EXECUTE FUNCTION protect_final_ballot_area_requirements();

        CREATE FUNCTION require_geography_before_ballot_publication() RETURNS trigger AS $$
        BEGIN
          IF NEW.status = 'published' AND OLD.status <> 'published'
             AND NOT EXISTS (
               SELECT 1 FROM ballot_geographic_requirements
               WHERE ballot_version_id = NEW.id
             ) THEN
            RAISE EXCEPTION 'a ballot must have geographic requirements before publication';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ballot_versions_require_geography
        BEFORE UPDATE OF status ON ballot_versions
        FOR EACH ROW EXECUTE FUNCTION require_geography_before_ballot_publication();
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
