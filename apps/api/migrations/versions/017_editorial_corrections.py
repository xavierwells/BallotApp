"""Retain field corrections and explicitly carry forward unchanged reviews.

Revision ID: 017_editorial_corrections
Revises: 016_review_policy
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "017_editorial_corrections"
down_revision = "016_review_policy"
branch_labels = depends_on = None


def upgrade() -> None:
    # NULL on old batches means their original content_hash. No historical rows
    # are rewritten, and the existing immutability triggers stay enabled.
    op.add_column("editorial_batches", sa.Column("intake_content_hash", sa.String(64)))
    op.add_column("editorial_decisions", sa.Column("carried_from_decision_id", sa.BigInteger()))
    op.create_unique_constraint("uq_editorial_decision_publication", "editorial_decisions", ["id", "publication_id"])
    op.create_foreign_key("fk_editorial_carried_review_publication", "editorial_decisions", "editorial_decisions",
                          ["carried_from_decision_id", "publication_id"], ["id", "publication_id"])
    op.create_table(
        "editorial_corrections",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("race_key", sa.String(255), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changes", postgresql.JSONB(), nullable=False),
        sa.Column("note", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["parent_batch_id", "publication_id"], ["editorial_batches.id", "editorial_batches.publication_id"]),
        sa.ForeignKeyConstraint(["batch_id", "publication_id"], ["editorial_batches.id", "editorial_batches.publication_id"]),
        sa.ForeignKeyConstraint(["actor_id", "publication_id"], ["editorial_users.id", "editorial_users.publication_id"]),
        sa.CheckConstraint("parent_batch_id <> batch_id", name="ck_editorial_correction_revision"),
    )
    op.create_index("ix_editorial_correction_batch", "editorial_corrections", ["publication_id", "batch_id"])
    op.execute("CREATE TRIGGER editorial_corrections_immutable BEFORE UPDATE OR DELETE ON editorial_corrections "
               "FOR EACH ROW EXECUTE FUNCTION protect_source_citations()")


def downgrade() -> None:
    raise NotImplementedError("Provenance migrations are forward-only; restore a verified backup.")
