"""Create one editorial alert per approved source whose review is overdue.

This command intentionally performs no network operation. It only compares a
previously scheduled review time with the current time and writes operational
alert metadata.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.cli.record_source_check import parse_utc_datetime
from app.database import get_engine


def queue_overdue_alerts(*, engine: Engine, now: datetime) -> int:
    """Insert idempotent overdue alerts for approved, enabled, due sources."""
    with engine.begin() as connection:
        created_alerts = connection.execute(
            text(
                "INSERT INTO source_alerts (id, authority_source_registry_id, alert_type, created_at) "
                "SELECT gen_random_uuid(), id, 'verification_overdue', :now "
                "FROM authority_source_registry "
                "WHERE approval_status IN ('pending_review', 'approved') "
                "AND permitted_use IN ('direct_link_manual_check', 'private_retention', 'public_copy') "
                "AND monitoring_class <> 'disabled' "
                "AND next_check_at IS NOT NULL "
                "AND next_check_at <= :now "
                "ON CONFLICT DO NOTHING "
                "RETURNING id"
            ),
            {"now": now},
        ).scalars().all()
    return len(created_alerts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue overdue approved source checks without retrieving sources.")
    parser.add_argument("--now", type=parse_utc_datetime, default=datetime.now(timezone.utc))
    arguments = parser.parse_args()
    count = queue_overdue_alerts(engine=get_engine(), now=arguments.now)
    print(f"Overdue source alerts queued: {count}")


if __name__ == "__main__":
    main()
