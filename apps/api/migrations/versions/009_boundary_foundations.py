"""Add PostGIS and provenance-first versioned boundary storage.

Revision ID: 009_boundary_foundations
Revises: 008_source_use_scope
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "009_boundary_foundations"
down_revision = "008_source_use_scope"
branch_labels = None
depends_on = None


uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "geographic_areas",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "authority_id",
            uuid,
            sa.ForeignKey("election_authorities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("area_type", sa.String(40), nullable=False),
        sa.Column("external_identifier", sa.String(255), nullable=True),
        sa.Column("status", sa.String(24), server_default="draft", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("authority_id", "slug", name="uq_geographic_areas_authority_slug"),
        sa.UniqueConstraint("id", "authority_id", name="uq_geographic_areas_id_authority"),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_geographic_areas_slug"),
        sa.CheckConstraint(
            "area_type IN ('county', 'municipality', 'voting_precinct', 'school_district', "
            "'state_legislative', 'federal_congressional', 'judicial', 'special_district', 'other')",
            name="ck_geographic_areas_type",
        ),
        sa.CheckConstraint("status IN ('draft', 'active', 'retired')", name="ck_geographic_areas_status"),
    )
    op.create_index(
        "ix_geographic_areas_authority_type_status",
        "geographic_areas",
        ["authority_id", "area_type", "status"],
    )

    op.create_table(
        "boundary_datasets",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("authority_id", uuid, nullable=False),
        sa.Column("authority_source_registry_id", uuid, nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("source_effective_date", sa.Date(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), server_default="registered", nullable=False),
        sa.Column("reviewer_reference", sa.String(128), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["authority_source_registry_id", "authority_id"],
            ["authority_source_registry.id", "authority_source_registry.authority_id"],
            name="fk_boundary_datasets_registry_authority",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("id", "authority_id", name="uq_boundary_datasets_id_authority"),
        sa.CheckConstraint(
            "status IN ('registered', 'validated', 'imported', 'rejected')",
            name="ck_boundary_datasets_status",
        ),
        sa.CheckConstraint(
            "status NOT IN ('validated', 'imported', 'rejected') OR "
            "(reviewer_reference IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_boundary_datasets_reviewed_status",
        ),
    )
    op.create_index(
        "ix_boundary_datasets_authority_status",
        "boundary_datasets",
        ["authority_id", "status", "checked_at"],
    )

    op.create_table(
        "boundary_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("authority_id", uuid, nullable=False),
        sa.Column("geographic_area_id", uuid, nullable=False),
        sa.Column("boundary_dataset_id", uuid, nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("geometry_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), server_default="draft", nullable=False),
        sa.Column("verified_by_reference", sa.String(128), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_boundary_version_id", uuid, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["geographic_area_id", "authority_id"],
            ["geographic_areas.id", "geographic_areas.authority_id"],
            name="fk_boundary_versions_area_authority",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["boundary_dataset_id", "authority_id"],
            ["boundary_datasets.id", "boundary_datasets.authority_id"],
            name="fk_boundary_versions_dataset_authority",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_boundary_version_id"],
            ["boundary_versions.id"],
            name="fk_boundary_versions_supersedes",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_boundary_versions_effective_dates",
        ),
        sa.CheckConstraint(
            "geometry_checksum_sha256 ~ '^[A-Fa-f0-9]{64}$'",
            name="ck_boundary_versions_sha256",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'verified', 'superseded', 'retired')",
            name="ck_boundary_versions_status",
        ),
        sa.CheckConstraint(
            "status = 'draft' OR "
            "(effective_from IS NOT NULL AND verified_by_reference IS NOT NULL AND verified_at IS NOT NULL)",
            name="ck_boundary_versions_verified_status",
        ),
        sa.CheckConstraint(
            "supersedes_boundary_version_id IS NULL OR supersedes_boundary_version_id <> id",
            name="ck_boundary_versions_not_self_superseding",
        ),
    )
    # Keeping the spatial type in SQL avoids adding GeoAlchemy solely for DDL.
    op.execute(
        "ALTER TABLE boundary_versions "
        "ADD COLUMN boundary geometry(MULTIPOLYGON, 4326) NOT NULL"
    )
    op.create_check_constraint(
        "ck_boundary_versions_valid_geometry",
        "boundary_versions",
        "ST_IsValid(boundary)",
    )
    op.create_index(
        "ix_boundary_versions_area_effective",
        "boundary_versions",
        ["geographic_area_id", "effective_from", "effective_to", "status"],
    )
    op.execute(
        "CREATE INDEX ix_boundary_versions_boundary_gist "
        "ON boundary_versions USING GIST (boundary)"
    )

    op.execute(
        """
        CREATE FUNCTION prevent_final_boundary_dataset_mutation() RETURNS trigger AS $$
        BEGIN
          IF OLD.status IN ('imported', 'rejected') THEN
            RAISE EXCEPTION 'final boundary datasets are immutable; register a replacement dataset';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER boundary_datasets_final_immutable
        BEFORE UPDATE OR DELETE ON boundary_datasets
        FOR EACH ROW EXECUTE FUNCTION prevent_final_boundary_dataset_mutation();

        CREATE FUNCTION prevent_verified_boundary_mutation() RETURNS trigger AS $$
        BEGIN
          IF OLD.status IN ('verified', 'superseded', 'retired') THEN
            RAISE EXCEPTION 'verified boundary versions are immutable; create a superseding boundary version';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER boundary_versions_verified_immutable
        BEFORE UPDATE OR DELETE ON boundary_versions
        FOR EACH ROW EXECUTE FUNCTION prevent_verified_boundary_mutation();
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
