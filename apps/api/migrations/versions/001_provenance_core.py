"""Create the provenance-first civic information core.

Revision ID: 001_provenance_core
Revises:
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "001_provenance_core"
down_revision = None
branch_labels = None
depends_on = None


uuid = postgresql.UUID(as_uuid=True)
json = postgresql.JSONB(astext_type=sa.Text())

claim_type = postgresql.ENUM(
    "verified_fact",
    "candidate_statement",
    "editorial_analysis",
    "community_tip",
    name="claim_type",
    create_type=False,
)
editorial_status = postgresql.ENUM(
    "draft",
    "needs_review",
    "verified",
    "published",
    "retracted",
    "superseded",
    name="editorial_status",
    create_type=False,
)
source_type = postgresql.ENUM(
    "official_document",
    "campaign_response",
    "public_record",
    "news_report",
    "community_submission",
    name="source_type",
    create_type=False,
)
verification_action = postgresql.ENUM(
    "created",
    "verified",
    "published",
    "corrected",
    "retracted",
    "superseded",
    name="verification_action",
    create_type=False,
)
ballot_publication_status = postgresql.ENUM(
    "draft",
    "verified",
    "published",
    "superseded",
    "archived",
    name="ballot_publication_status",
    create_type=False,
)
enums = (claim_type, editorial_status, source_type, verification_action, ballot_publication_status)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in enums:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_organizations_slug"),
    )
    op.create_table(
        "publications",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("organization_id", "slug", name="uq_publications_organization_slug"),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", name="ck_publications_slug"),
    )
    op.create_index("ix_publications_organization_id", "publications", ["organization_id"])

    op.create_table(
        "documents",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("publisher_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("source_license", sa.String(255), nullable=True),
        sa.Column("storage_key", sa.String(1024), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("document_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_authoritative", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("publication_id", "checksum_sha256", name="uq_documents_publication_checksum"),
        sa.CheckConstraint("checksum_sha256 ~ '^[A-Fa-f0-9]{64}$'", name="ck_documents_sha256"),
    )
    op.create_index("ix_documents_publication_source_type", "documents", ["publication_id", "source_type"])

    op.create_table(
        "elections",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("authority_name", sa.String(255), nullable=False),
        sa.Column("jurisdiction_name", sa.String(255), nullable=False),
        sa.Column("election_date", sa.Date(), nullable=False),
        sa.Column("election_type", sa.String(100), nullable=False),
        sa.Column("official_document_id", uuid, sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint(
            "publication_id", "authority_name", "jurisdiction_name", "election_date", "election_type",
            name="uq_elections_publication_authority_date_type",
        ),
    )
    op.create_index("ix_elections_publication_date", "elections", ["publication_id", "election_date"])

    op.create_table(
        "offices",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("government_level", sa.String(80), nullable=False),
        sa.Column("jurisdiction_name", sa.String(255), nullable=False),
        sa.Column("term_description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("publication_id", "name", "jurisdiction_name", name="uq_offices_publication_name_jurisdiction"),
    )
    op.create_index("ix_offices_publication_level", "offices", ["publication_id", "government_level"])

    op.create_table(
        "races",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("election_id", uuid, sa.ForeignKey("elections.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("office_id", uuid, sa.ForeignKey("offices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("district_label", sa.String(255), nullable=True),
        sa.Column("ballot_title", sa.String(500), nullable=False),
        sa.Column("seats_available", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("seats_available > 0", name="ck_races_seats_available"),
    )
    op.create_index("ix_races_publication_election", "races", ["publication_id", "election_id"])

    op.create_table(
        "propositions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("election_id", uuid, sa.ForeignKey("elections.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("official_document_id", uuid, sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("external_identifier", sa.String(255), nullable=True),
        sa.Column("ballot_title", sa.String(500), nullable=False),
        sa.Column("official_text", sa.Text(), nullable=False),
        sa.Column("source_page", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_propositions_publication_election", "propositions", ["publication_id", "election_id"])
    op.create_index(
        "uq_propositions_external_identifier",
        "propositions",
        ["publication_id", "election_id", "external_identifier"],
        unique=True,
        postgresql_where=sa.text("external_identifier IS NOT NULL"),
    )

    op.create_table(
        "ballot_versions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("election_id", uuid, sa.ForeignKey("elections.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("official_document_id", uuid, sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("external_identifier", sa.String(255), nullable=True),
        sa.Column("status", ballot_publication_status, server_default="draft", nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_ballot_version_id", uuid, sa.ForeignKey("ballot_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "(status IN ('published', 'superseded', 'archived')) = (published_at IS NOT NULL)",
            name="ck_ballot_versions_publication_time",
        ),
        sa.CheckConstraint(
            "supersedes_ballot_version_id IS NULL OR supersedes_ballot_version_id <> id",
            name="ck_ballot_versions_not_self_superseding",
        ),
    )
    op.create_index("ix_ballot_versions_publication_election_status", "ballot_versions", ["publication_id", "election_id", "status"])
    op.create_index(
        "uq_ballot_versions_external_identifier",
        "ballot_versions",
        ["publication_id", "election_id", "external_identifier"],
        unique=True,
        postgresql_where=sa.text("external_identifier IS NOT NULL"),
    )

    op.create_table(
        "candidates",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("race_id", uuid, sa.ForeignKey("races.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_document_id", uuid, sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("ballot_label", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("race_id", "canonical_name", name="uq_candidates_race_canonical_name"),
    )
    op.create_index("ix_candidates_publication_race", "candidates", ["publication_id", "race_id"])

    op.create_table(
        "ballot_items",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ballot_version_id", uuid, sa.ForeignKey("ballot_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("race_id", uuid, sa.ForeignKey("races.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("proposition_id", uuid, sa.ForeignKey("propositions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("sequence", sa.SmallInteger(), nullable=False),
        sa.Column("source_page", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("ballot_version_id", "sequence", name="uq_ballot_items_version_sequence"),
        sa.CheckConstraint("sequence > 0", name="ck_ballot_items_sequence"),
        sa.CheckConstraint(
            "(race_id IS NOT NULL)::integer + (proposition_id IS NOT NULL)::integer = 1",
            name="ck_ballot_items_one_subject",
        ),
    )
    op.create_index("ix_ballot_items_publication_version", "ballot_items", ["publication_id", "ballot_version_id"])

    op.create_table(
        "source_claims",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_id", uuid, sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("claim_type", claim_type, nullable=False),
        sa.Column("editorial_status", editorial_status, server_default="draft", nullable=False),
        sa.Column("subject_type", sa.String(80), nullable=False),
        sa.Column("subject_id", uuid, nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("source_page", sa.String(80), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("confidence", sa.SmallInteger(), nullable=True),
        sa.Column("first_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_source_claim_id", uuid, sa.ForeignKey("source_claims.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 100", name="ck_source_claims_confidence"),
        sa.CheckConstraint(
            "editorial_status <> 'published' OR (published_at IS NOT NULL AND last_verified_at IS NOT NULL)",
            name="ck_source_claims_published_verification_time",
        ),
        sa.CheckConstraint(
            "supersedes_source_claim_id IS NULL OR supersedes_source_claim_id <> id",
            name="ck_source_claims_not_self_superseding",
        ),
    )
    op.create_index("ix_source_claims_publication_status", "source_claims", ["publication_id", "editorial_status"])
    op.create_index("ix_source_claims_subject", "source_claims", ["publication_id", "subject_type", "subject_id"])
    op.create_index("ix_source_claims_document", "source_claims", ["document_id"])

    op.create_table(
        "verification_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_claim_id", uuid, sa.ForeignKey("source_claims.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("action", verification_action, nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", uuid, nullable=False),
        sa.Column("actor_reference", sa.String(128), nullable=False),
        sa.Column("actor_role", sa.String(80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("before_snapshot", json, nullable=True),
        sa.Column("after_snapshot", json, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_verification_events_claim_time", "verification_events", ["source_claim_id", "occurred_at"])
    op.create_index("ix_verification_events_target_time", "verification_events", ["publication_id", "target_type", "target_id", "occurred_at"])

    for statement in (
        """
        CREATE FUNCTION prevent_document_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'documents are immutable; register a replacement document instead';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER documents_immutable
        BEFORE UPDATE OR DELETE ON documents
        FOR EACH ROW EXECUTE FUNCTION prevent_document_mutation();
        """,
        """
        CREATE FUNCTION prevent_verification_event_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'verification events are immutable';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER verification_events_immutable
        BEFORE UPDATE OR DELETE ON verification_events
        FOR EACH ROW EXECUTE FUNCTION prevent_verification_event_mutation();
        """,
        """
        CREATE FUNCTION prevent_published_claim_mutation() RETURNS trigger AS $$
        BEGIN
          IF OLD.editorial_status = 'published' THEN
            RAISE EXCEPTION 'published source claims are immutable; create a superseding claim';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER source_claims_published_immutable
        BEFORE UPDATE OR DELETE ON source_claims
        FOR EACH ROW EXECUTE FUNCTION prevent_published_claim_mutation();
        """,
        """
        CREATE FUNCTION prevent_published_ballot_version_mutation() RETURNS trigger AS $$
        BEGIN
          IF OLD.status IN ('published', 'superseded', 'archived') THEN
            RAISE EXCEPTION 'published ballot versions are immutable; create a superseding ballot version';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ballot_versions_published_immutable
        BEFORE UPDATE OR DELETE ON ballot_versions
        FOR EACH ROW EXECUTE FUNCTION prevent_published_ballot_version_mutation();
        """,
        """
        CREATE FUNCTION require_claim_publication_event() RETURNS trigger AS $$
        BEGIN
          IF NEW.editorial_status = 'published' AND NOT EXISTS (
            SELECT 1 FROM verification_events
            WHERE source_claim_id = NEW.id
              AND action IN ('verified', 'published', 'corrected')
          ) THEN
            RAISE EXCEPTION 'a published source claim requires a linked verification event';
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE CONSTRAINT TRIGGER source_claims_require_publication_event
        AFTER INSERT OR UPDATE OF editorial_status ON source_claims
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION require_claim_publication_event();
        """,
    ):
        op.execute(statement)


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
