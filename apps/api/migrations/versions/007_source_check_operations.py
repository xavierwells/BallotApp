"""Synchronize source-check schedules and open investigation alerts.

Revision ID: 007_source_check_operations
Revises: 006_source_alert_lifecycle
Create Date: 2026-08-20
"""

from alembic import op


revision = "007_source_check_operations"
down_revision = "006_source_alert_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION sync_source_registry_schedule_after_check() RETURNS trigger AS $$
        BEGIN
          UPDATE authority_source_registry
          SET last_checked_at = NEW.checked_at,
              next_check_at = NEW.next_check_at
          WHERE id = NEW.authority_source_registry_id
            AND (last_checked_at IS NULL OR last_checked_at <= NEW.checked_at);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER source_registry_schedule_after_check
        AFTER INSERT ON source_verification_checks
        FOR EACH ROW EXECUTE FUNCTION sync_source_registry_schedule_after_check();
        """
    )
    op.execute(
        """
        CREATE FUNCTION open_investigation_alert_after_source_check() RETURNS trigger AS $$
        DECLARE
          mapped_alert_type text;
        BEGIN
          mapped_alert_type := CASE NEW.result
            WHEN 'changed' THEN 'source_changed'
            WHEN 'unavailable' THEN 'source_unavailable'
            WHEN 'terms_changed' THEN 'terms_changed'
            ELSE NULL
          END;
          IF mapped_alert_type IS NOT NULL THEN
            INSERT INTO source_alerts (
              id, authority_source_registry_id, source_verification_check_id, alert_type
            ) VALUES (
              gen_random_uuid(), NEW.authority_source_registry_id, NEW.id, mapped_alert_type
            ) ON CONFLICT DO NOTHING;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER source_alerts_open_after_source_check
        AFTER INSERT ON source_verification_checks
        FOR EACH ROW EXECUTE FUNCTION open_investigation_alert_after_source_check();
        """
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
