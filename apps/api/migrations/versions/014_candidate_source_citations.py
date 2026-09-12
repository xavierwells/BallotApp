"""Allow election-specific candidacies to cite multiple official documents.

Revision ID: 014_candidate_sources
Revises: 013_official_ballot_intake
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "014_candidate_sources"
down_revision = "013_official_ballot_intake"
branch_labels = None
depends_on = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # Migration 011 already created documents(id, publication_id) for the same
    # tenant-safe composite foreign-key pattern. Reuse that constraint here.
    op.create_unique_constraint("uq_elections_id_publication", "elections", ["id", "publication_id"])
    op.create_unique_constraint("uq_candidates_id_publication", "candidates", ["id", "publication_id"])
    op.alter_column("elections", "official_document_id", existing_type=uuid, nullable=True)
    op.create_table(
        "election_source_citations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("election_id", uuid, nullable=False),
        sa.Column("document_id", uuid, nullable=False),
        sa.Column("evidence_role", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("election_id", "document_id", name="uq_election_source_citation"),
        sa.ForeignKeyConstraint(["election_id", "publication_id"], ["elections.id", "elections.publication_id"],
                                name="fk_election_citation_tenant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id", "publication_id"], ["documents.id", "documents.publication_id"],
                                name="fk_election_citation_document_tenant", ondelete="RESTRICT"),
        sa.CheckConstraint(
            "evidence_role IN ('candidate_certification', 'official_ballot', 'election_notice', 'correction')",
            name="ck_election_citation_role",
        ),
    )
    op.create_index("ix_election_source_citations_publication_election", "election_source_citations",
                    ["publication_id", "election_id"])
    op.execute(
        """
        INSERT INTO election_source_citations
          (id, publication_id, election_id, document_id, evidence_role)
        SELECT gen_random_uuid(), publication_id, id, official_document_id, 'official_ballot'
        FROM elections WHERE official_document_id IS NOT NULL
        ON CONFLICT DO NOTHING;
        """
    )
    op.add_column("candidates", sa.Column("party_label", sa.String(80), nullable=True))
    op.alter_column("candidates", "candidate_document_id", existing_type=uuid, nullable=True)
    op.create_table(
        "candidate_source_citations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candidate_id", uuid, nullable=False),
        sa.Column("document_id", uuid, nullable=False),
        sa.Column("source_page", sa.String(80), nullable=False),
        sa.Column("evidence_role", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("candidate_id", "document_id", "source_page", name="uq_candidate_source_citation"),
        sa.ForeignKeyConstraint(["candidate_id", "publication_id"], ["candidates.id", "candidates.publication_id"],
                                name="fk_candidate_citation_tenant", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id", "publication_id"], ["documents.id", "documents.publication_id"],
                                name="fk_candidate_citation_document_tenant", ondelete="RESTRICT"),
        sa.CheckConstraint("NULLIF(BTRIM(source_page), '') IS NOT NULL", name="ck_candidate_citation_page"),
        sa.CheckConstraint(
            "evidence_role IN ('candidate_certification', 'official_ballot', 'candidate_filing', 'correction')",
            name="ck_candidate_citation_role",
        ),
    )
    op.create_index(
        "ix_candidate_source_citations_publication_candidate",
        "candidate_source_citations",
        ["publication_id", "candidate_id"],
    )
    op.execute(
        """
        INSERT INTO candidate_source_citations
          (id, publication_id, candidate_id, document_id, source_page, evidence_role)
        SELECT gen_random_uuid(), c.publication_id, c.id, c.candidate_document_id,
               COALESCE(MIN(bi.source_page), 'legacy citation unavailable'), 'official_ballot'
        FROM candidates c
        LEFT JOIN ballot_items bi ON bi.race_id = c.race_id
        WHERE c.candidate_document_id IS NOT NULL
        GROUP BY c.publication_id, c.id, c.candidate_document_id
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_source_citations() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'source citations are immutable; add a correction citation instead';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER election_source_citations_immutable
        BEFORE UPDATE OR DELETE ON election_source_citations
        FOR EACH ROW EXECUTE FUNCTION protect_source_citations();

        CREATE TRIGGER candidate_source_citations_immutable
        BEFORE UPDATE OR DELETE ON candidate_source_citations
        FOR EACH ROW EXECUTE FUNCTION protect_source_citations();
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
