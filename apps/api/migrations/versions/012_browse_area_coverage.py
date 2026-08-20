"""Store provenance-first coarse browse areas and coverage estimates.

Revision ID: 012_browse_area_coverage
Revises: 011_ballot_area_requirements
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "012_browse_area_coverage"
down_revision = "011_ballot_area_requirements"
branch_labels = None
depends_on = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "browse_areas",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, nullable=False),
        sa.Column("area_type", sa.String(16), nullable=False),
        sa.Column("query_key", sa.String(255), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("source_document_id", uuid, nullable=False),
        sa.Column("source_vintage", sa.String(64), nullable=False),
        sa.Column("geometry_checksum_sha256", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("verified_by_reference", sa.String(128), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_document_id", "publication_id"],
            ["documents.id", "documents.publication_id"],
            name="fk_browse_areas_document_publication",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "publication_id", "area_type", "query_key", "source_vintage",
            name="uq_browse_areas_query_vintage",
        ),
        sa.UniqueConstraint("id", "publication_id", name="uq_browse_areas_id_publication"),
        sa.CheckConstraint("area_type IN ('zip', 'city', 'county')", name="ck_browse_areas_type"),
        sa.CheckConstraint("query_key = lower(btrim(query_key))", name="ck_browse_areas_normalized_query"),
        sa.CheckConstraint(
            "geometry_checksum_sha256 IS NULL OR geometry_checksum_sha256 ~ '^[A-Fa-f0-9]{64}$'",
            name="ck_browse_areas_sha256",
        ),
        sa.CheckConstraint("status IN ('draft', 'verified', 'retired')", name="ck_browse_areas_status"),
        sa.CheckConstraint(
            "status = 'draft' OR (verified_by_reference IS NOT NULL AND verified_at IS NOT NULL)",
            name="ck_browse_areas_verified_status",
        ),
    )
    op.execute("ALTER TABLE browse_areas ADD COLUMN boundary geometry(MULTIPOLYGON, 4326)")
    op.create_check_constraint(
        "ck_browse_areas_valid_boundary", "browse_areas", "boundary IS NULL OR ST_IsValid(boundary)"
    )
    op.execute("CREATE INDEX ix_browse_areas_boundary_gist ON browse_areas USING GIST (boundary)")
    op.create_index(
        "ix_browse_areas_lookup", "browse_areas", ["publication_id", "area_type", "query_key", "status"]
    )

    op.create_table(
        "browse_coverage_estimates",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, nullable=False),
        sa.Column("browse_area_id", uuid, nullable=False),
        sa.Column("target_kind", sa.String(24), nullable=False),
        sa.Column("target_ballot_version_id", uuid, nullable=True),
        sa.Column("target_geographic_area_id", uuid, nullable=True),
        sa.Column("target_authority_id", uuid, nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("estimated_share_percent", sa.Numeric(7, 4), nullable=False),
        sa.Column("coverage_basis", sa.String(48), nullable=False),
        sa.Column("numerator", sa.BigInteger(), nullable=False),
        sa.Column("denominator", sa.BigInteger(), nullable=False),
        sa.Column("methodology", sa.Text(), nullable=False),
        sa.Column("calculation_version", sa.String(64), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), server_default="draft", nullable=False),
        sa.Column("verified_by_reference", sa.String(128), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(
            ["browse_area_id", "publication_id"], ["browse_areas.id", "browse_areas.publication_id"],
            name="fk_browse_estimates_area_publication", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_ballot_version_id", "publication_id"],
            ["ballot_versions.id", "ballot_versions.publication_id"],
            name="fk_browse_estimates_ballot_publication", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_geographic_area_id", "target_authority_id"],
            ["geographic_areas.id", "geographic_areas.authority_id"],
            name="fk_browse_estimates_area_authority", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_authority_id", "publication_id"],
            ["election_authorities.id", "election_authorities.publication_id"],
            name="fk_browse_estimates_authority_publication", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("target_kind IN ('ballot', 'geographic_area')", name="ck_browse_estimates_target_kind"),
        sa.CheckConstraint(
            "(target_kind = 'ballot' AND target_ballot_version_id IS NOT NULL "
            "AND target_geographic_area_id IS NULL AND target_authority_id IS NULL) OR "
            "(target_kind = 'geographic_area' AND target_ballot_version_id IS NULL "
            "AND target_geographic_area_id IS NOT NULL AND target_authority_id IS NOT NULL)",
            name="ck_browse_estimates_one_target",
        ),
        sa.CheckConstraint("rank > 0", name="ck_browse_estimates_positive_rank"),
        sa.CheckConstraint(
            "estimated_share_percent >= 0 AND estimated_share_percent <= 100",
            name="ck_browse_estimates_percent",
        ),
        sa.CheckConstraint("numerator >= 0 AND denominator > 0 AND numerator <= denominator", name="ck_browse_estimates_counts"),
        sa.CheckConstraint(
            "abs(estimated_share_percent - round(numerator::numeric * 100 / denominator, 4)) <= 0.0001",
            name="ck_browse_estimates_calculation",
        ),
        sa.CheckConstraint(
            "coverage_basis IN ('residential_population_estimate', 'address_coverage_estimate', 'land_area_estimate')",
            name="ck_browse_estimates_basis",
        ),
        sa.CheckConstraint("status IN ('draft', 'verified', 'retired')", name="ck_browse_estimates_status"),
        sa.CheckConstraint(
            "status = 'draft' OR (verified_by_reference IS NOT NULL AND verified_at IS NOT NULL)",
            name="ck_browse_estimates_verified_status",
        ),
        sa.UniqueConstraint("browse_area_id", "target_kind", "rank", name="uq_browse_estimates_rank"),
    )
    op.create_index(
        "ix_browse_estimates_lookup",
        "browse_coverage_estimates",
        ["browse_area_id", "target_kind", "status", "rank"],
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_browse_estimates_ballot ON browse_coverage_estimates "
        "(browse_area_id, target_ballot_version_id) WHERE target_kind = 'ballot'"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_browse_estimates_geographic_area ON browse_coverage_estimates "
        "(browse_area_id, target_geographic_area_id) WHERE target_kind = 'geographic_area'"
    )
    op.create_unique_constraint(
        "uq_browse_estimates_id_publication", "browse_coverage_estimates", ["id", "publication_id"]
    )

    op.create_table(
        "browse_coverage_evidence",
        sa.Column("coverage_estimate_id", uuid, nullable=False),
        sa.Column("source_document_id", uuid, nullable=False),
        sa.Column("publication_id", uuid, nullable=False),
        sa.Column("evidence_role", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["coverage_estimate_id", "publication_id"],
            ["browse_coverage_estimates.id", "browse_coverage_estimates.publication_id"],
            name="fk_browse_evidence_estimate_publication", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id", "publication_id"], ["documents.id", "documents.publication_id"],
            name="fk_browse_evidence_document_publication", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("coverage_estimate_id", "source_document_id", name="pk_browse_coverage_evidence"),
        sa.CheckConstraint(
            "evidence_role IN ('browse_boundary', 'population', 'target_boundary', 'ballot_definition', 'methodology')",
            name="ck_browse_evidence_role",
        ),
    )
    op.execute(
        """
        CREATE FUNCTION protect_final_browse_area() RETURNS trigger AS $$
        BEGIN
          IF OLD.status IN ('verified', 'retired') THEN
            RAISE EXCEPTION 'verified browse areas are immutable; register a replacement vintage';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER browse_areas_final_immutable
        BEFORE UPDATE OR DELETE ON browse_areas
        FOR EACH ROW EXECUTE FUNCTION protect_final_browse_area();

        CREATE FUNCTION protect_final_browse_estimate() RETURNS trigger AS $$
        BEGIN
          IF OLD.status IN ('verified', 'retired') THEN
            RAISE EXCEPTION 'verified browse coverage estimates are immutable; calculate a replacement';
          END IF;
          IF TG_OP <> 'DELETE' THEN
            IF NEW.status = 'verified' AND OLD.status <> 'verified'
               AND NOT EXISTS (
                 SELECT 1 FROM browse_coverage_evidence
                 WHERE coverage_estimate_id = NEW.id
               ) THEN
              RAISE EXCEPTION 'verified browse coverage estimates require source evidence';
            END IF;
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER browse_estimates_final_immutable
        BEFORE UPDATE OR DELETE ON browse_coverage_estimates
        FOR EACH ROW EXECUTE FUNCTION protect_final_browse_estimate();

        CREATE FUNCTION protect_final_browse_evidence() RETURNS trigger AS $$
        DECLARE estimate_status text;
        BEGIN
          SELECT status INTO estimate_status FROM browse_coverage_estimates
          WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.coverage_estimate_id ELSE NEW.coverage_estimate_id END;
          IF estimate_status IN ('verified', 'retired') THEN
            RAISE EXCEPTION 'verified browse coverage evidence is immutable';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER browse_evidence_final_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON browse_coverage_evidence
        FOR EACH ROW EXECUTE FUNCTION protect_final_browse_evidence();
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
