"""Add the hybrid stale-source alert lifecycle.

Revision ID: 006_source_alert_lifecycle
Revises: 005_source_monitoring
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "006_source_alert_lifecycle"
down_revision = "005_source_monitoring"
branch_labels = None
depends_on = None


uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "source_alerts",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("authority_source_registry_id", uuid, sa.ForeignKey("authority_source_registry.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_verification_check_id", uuid, sa.ForeignKey("source_verification_checks.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("alert_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), server_default="open", nullable=False),
        sa.Column("resolution", sa.String(32), nullable=True),
        sa.Column("resolved_by_reference", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "alert_type IN ('verification_overdue', 'source_changed', 'source_unavailable', 'terms_changed')",
            name="ck_source_alerts_type",
        ),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_source_alerts_status"),
        sa.CheckConstraint(
            "(status = 'open' AND resolution IS NULL AND resolved_at IS NULL) OR "
            "(status = 'resolved' AND resolution IN ('automatic_unchanged', 'editor_handled', 'source_retired') "
            "AND resolved_at IS NOT NULL)",
            name="ck_source_alerts_resolution",
        ),
    )
    op.create_index("ix_source_alerts_source_status", "source_alerts", ["authority_source_registry_id", "status", "created_at"])
    op.create_index(
        "uq_source_alerts_open_type",
        "source_alerts",
        ["authority_source_registry_id", "alert_type"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    op.execute(
        """
        CREATE FUNCTION resolve_stale_alert_after_manual_unchanged_check() RETURNS trigger AS $$
        BEGIN
          IF NEW.result = 'unchanged' AND NEW.check_method = 'manual' THEN
            UPDATE source_alerts
            SET status = 'resolved',
                resolution = 'automatic_unchanged',
                source_verification_check_id = NEW.id,
                resolved_at = NEW.checked_at
            WHERE authority_source_registry_id = NEW.authority_source_registry_id
              AND alert_type = 'verification_overdue'
              AND status = 'open';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER source_alerts_resolve_after_manual_unchanged_check
        AFTER INSERT ON source_verification_checks
        FOR EACH ROW EXECUTE FUNCTION resolve_stale_alert_after_manual_unchanged_check();
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
