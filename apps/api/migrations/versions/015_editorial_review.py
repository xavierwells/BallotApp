"""Private, versioned review batches and provisioned staff identities.

Revision ID: 015_editorial_review
Revises: 014_candidate_sources
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015_editorial_review"
down_revision = "014_candidate_sources"
branch_labels = depends_on = None
uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "editorial_users",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id"), nullable=False),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("failed_logins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("id", "publication_id", name="uq_editorial_user_publication"),
        sa.CheckConstraint("username ~ '^[a-z0-9][a-z0-9._-]{2,79}$'", name="ck_editorial_username"),
    )
    op.create_table(
        "editorial_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("editorial_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_editorial_session_expiry", "editorial_sessions", ["expires_at"])
    op.create_table(
        "editorial_batches",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("version", sa.BigInteger(), sa.Identity(), nullable=False, unique=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id"), nullable=False),
        sa.Column("batch_key", sa.String(255), nullable=False),
        sa.Column("document_id", uuid, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("required_reviewers", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("id", "publication_id", name="uq_editorial_batch_publication"),
        sa.ForeignKeyConstraint(["document_id", "publication_id"], ["documents.id", "documents.publication_id"]),
        sa.CheckConstraint("required_reviewers IN (1, 2)", name="ck_editorial_review_count"),
    )
    op.create_index("ix_editorial_batch_latest", "editorial_batches", ["publication_id", "batch_key", "version"])
    op.create_table(
        "editorial_decisions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("publication_id", uuid, nullable=False),
        sa.Column("batch_id", uuid, nullable=False),
        sa.Column("reviewer_id", uuid, nullable=False),
        sa.Column("race_key", sa.String(255), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.String(2000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["batch_id", "publication_id"], ["editorial_batches.id", "editorial_batches.publication_id"]),
        sa.ForeignKeyConstraint(["reviewer_id", "publication_id"], ["editorial_users.id", "editorial_users.publication_id"]),
        sa.CheckConstraint("decision IN ('accepted', 'flagged')", name="ck_editorial_decision"),
        sa.CheckConstraint("decision <> 'flagged' OR length(trim(note)) > 0", name="ck_editorial_flag_note"),
    )
    op.create_index("ix_editorial_decision_batch", "editorial_decisions", ["batch_id", "id"])
    op.create_table(
        "editorial_promotions",
        sa.Column("batch_id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, nullable=False),
        sa.Column("actor_id", uuid, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["batch_id", "publication_id"], ["editorial_batches.id", "editorial_batches.publication_id"]),
        sa.ForeignKeyConstraint(["actor_id", "publication_id"], ["editorial_users.id", "editorial_users.publication_id"]),
    )
    for table in ("editorial_batches", "editorial_decisions", "editorial_promotions"):
        op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                   "FOR EACH ROW EXECUTE FUNCTION protect_source_citations()")


def downgrade() -> None:
    raise NotImplementedError("Provenance migrations are forward-only; restore a verified backup.")
