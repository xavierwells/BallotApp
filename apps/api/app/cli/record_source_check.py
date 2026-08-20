"""Record a completed manual source verification without retrieving a URL.

The command is operator-only until authenticated editorial workflows exist. It
records a human's observation and an explicitly supplied next due time; it
does not fetch or log the source URL, an entered address, or a document body.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.database import get_engine


ALLOWED_RESULTS = ("unchanged", "changed", "unavailable", "terms_changed")


def parse_utc_datetime(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and require a timezone offset."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include a UTC offset, for example 2026-08-20T12:00:00Z")
    return parsed.astimezone(timezone.utc)


def record_source_check(
    *,
    engine: Engine,
    organization_slug: str,
    publication_slug: str,
    authority_slug: str,
    source_slug: str,
    result: str,
    checker_reference: str,
    checked_at: datetime,
    next_check_at: datetime,
    notes: str | None,
) -> str:
    """Insert an immutable manual check for one approved, tenant-scoped source."""
    with engine.begin() as connection:
        source = connection.execute(
            text(
                "SELECT authority_source_registry.id, authority_source_registry.approval_status "
                "FROM organizations "
                "JOIN publications ON publications.organization_id = organizations.id "
                "JOIN election_authorities ON election_authorities.publication_id = publications.id "
                "JOIN authority_source_registry ON authority_source_registry.authority_id = election_authorities.id "
                "WHERE organizations.slug = :organization_slug "
                "AND publications.slug = :publication_slug "
                "AND election_authorities.slug = :authority_slug "
                "AND authority_source_registry.slug = :source_slug"
            ),
            {
                "organization_slug": organization_slug,
                "publication_slug": publication_slug,
                "authority_slug": authority_slug,
                "source_slug": source_slug,
            },
        ).mappings().one_or_none()
        if source is None:
            raise ValueError("authority source was not found in the specified organization and publication")
        if source["approval_status"] != "approved":
            raise ValueError("a source must be approved before it can enter the verification schedule")
        if next_check_at <= checked_at:
            raise ValueError("next check time must be after the completed check time")

        return str(
            connection.execute(
                text(
                    "INSERT INTO source_verification_checks "
                    "(id, authority_source_registry_id, checked_at, result, checker_reference, notes, next_check_at, check_method) "
                    "VALUES (gen_random_uuid(), :source_id, :checked_at, :result, :checker_reference, :notes, "
                    ":next_check_at, 'manual') RETURNING id"
                ),
                {
                    "source_id": source["id"],
                    "checked_at": checked_at,
                    "result": result,
                    "checker_reference": checker_reference,
                    "notes": notes,
                    "next_check_at": next_check_at,
                },
            ).scalar_one()
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a manual source verification without retrieving the source.")
    parser.add_argument("--organization-slug", required=True)
    parser.add_argument("--publication-slug", required=True)
    parser.add_argument("--authority-slug", required=True)
    parser.add_argument("--source-slug", required=True)
    parser.add_argument("--result", required=True, choices=ALLOWED_RESULTS)
    parser.add_argument("--checker-reference", required=True, help="Operator identifier; do not use an address or voter data.")
    parser.add_argument("--checked-at", type=parse_utc_datetime, default=datetime.now(timezone.utc))
    parser.add_argument("--next-check-at", type=parse_utc_datetime, required=True)
    parser.add_argument("--notes", help="Optional editorial note. Do not include PII, voter data, or private storage paths.")
    arguments = parser.parse_args()

    check_id = record_source_check(
        engine=get_engine(),
        organization_slug=arguments.organization_slug,
        publication_slug=arguments.publication_slug,
        authority_slug=arguments.authority_slug,
        source_slug=arguments.source_slug,
        result=arguments.result,
        checker_reference=arguments.checker_reference,
        checked_at=arguments.checked_at,
        next_check_at=arguments.next_check_at,
        notes=arguments.notes,
    )
    print(f"Manual source verification recorded: {check_id}")


if __name__ == "__main__":
    main()
