"""Explicit, immutable county-guide releases, separate from exact ballots."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "019_county_guide_publication"
down_revision = "018_shared_race_reviews"
branch_labels = depends_on = None
uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # No existing account is silently granted publication authority.
    op.add_column("editorial_users", sa.Column("can_publish", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_unique_constraint("uq_editorial_promotion_publication", "editorial_promotions", ["batch_id", "publication_id"])
    op.create_table("editorial_publisher_access_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("editorial_users.id"), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("database_actor", sa.Text(), nullable=False, server_default=sa.text("CURRENT_USER")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.execute("""
        CREATE FUNCTION record_publisher_access_change() RETURNS trigger AS $$
        BEGIN
          IF NEW.can_publish IS DISTINCT FROM OLD.can_publish THEN
            INSERT INTO editorial_publisher_access_events(user_id,allowed) VALUES(NEW.id,NEW.can_publish);
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER editorial_publisher_access_changed AFTER UPDATE OF can_publish ON editorial_users
          FOR EACH ROW EXECUTE FUNCTION record_publisher_access_change();
    """)
    op.create_table("county_guide_releases",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("publication_id", uuid, sa.ForeignKey("publications.id"), nullable=False),
        sa.Column("guide_key", sa.String(255), nullable=False),
        sa.Column("batch_id", uuid, nullable=False),
        sa.Column("actor_id", uuid, nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("id", "publication_id", "guide_key", name="uq_county_release_scope"),
        sa.ForeignKeyConstraint(["batch_id", "publication_id"], ["editorial_promotions.batch_id", "editorial_promotions.publication_id"]),
        sa.ForeignKeyConstraint(["actor_id", "publication_id"], ["editorial_users.id", "editorial_users.publication_id"]),
        sa.CheckConstraint("evidence_hash ~ '^[a-f0-9]{64}$'", name="ck_county_release_hash"),
        sa.CheckConstraint("COALESCE(payload->>'scope' = 'county_certification_guide' AND payload->>'exactMatch' = 'false' "
                           "AND payload->>'completeBallot' = 'false',false)", name="ck_county_guide_not_exact"))
    op.create_table("county_guide_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("publication_id", uuid, nullable=False),
        sa.Column("guide_key", sa.String(255), nullable=False),
        sa.Column("release_id", uuid, nullable=False),
        sa.Column("actor_id", uuid, nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("note", sa.String(2000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["release_id", "publication_id", "guide_key"],
                                ["county_guide_releases.id", "county_guide_releases.publication_id", "county_guide_releases.guide_key"]),
        sa.ForeignKeyConstraint(["actor_id", "publication_id"], ["editorial_users.id", "editorial_users.publication_id"]),
        sa.CheckConstraint("action IN ('publish','withdraw')", name="ck_county_guide_action"),
        sa.CheckConstraint("action <> 'withdraw' OR length(trim(note)) > 0", name="ck_county_withdrawal_note"))
    op.create_index("ix_county_guide_latest_event", "county_guide_events", ["publication_id", "guide_key", "id"])
    op.execute("""
        CREATE FUNCTION require_county_guide_publisher() RETURNS trigger AS $$
        BEGIN
          IF NOT EXISTS(SELECT 1 FROM editorial_users WHERE id=NEW.actor_id
            AND publication_id=NEW.publication_id AND active AND can_publish) THEN
            RAISE EXCEPTION 'county guide release requires an active publisher';
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
    """)
    for table in ("county_guide_releases", "county_guide_events"):
        op.execute(f"CREATE TRIGGER {table}_publisher BEFORE INSERT ON {table} "
                   "FOR EACH ROW EXECUTE FUNCTION require_county_guide_publisher()")
    for table in ("county_guide_releases", "county_guide_events", "editorial_publisher_access_events"):
        op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                   "FOR EACH ROW EXECUTE FUNCTION protect_source_citations()")


def downgrade() -> None:
    raise NotImplementedError("Provenance migrations are forward-only; restore a verified backup.")
