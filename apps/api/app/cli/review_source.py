"""Record an operator's source-review decision without contacting the source."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.cli.record_source_check import parse_utc_datetime
from app.database import get_engine


APPROVAL_STATUSES = ("pending_review", "approved", "rejected", "retired")
PERMITTED_USES = ("none", "direct_link_manual_check", "private_retention", "public_copy")
APPROVAL_FIELDS = (
    "terms_url",
    "source_license",
    "cost_model",
    "rate_limit",
    "retention_rule",
    "attribution_requirement",
    "redistribution_rights",
)


def review_source(
    *,
    engine: Engine,
    organization_slug: str,
    publication_slug: str,
    authority_slug: str,
    source_slug: str,
    approval_status: str,
    permitted_use: str,
    reviewer_reference: str,
    reviewed_at: datetime,
    review_notes: str | None,
    terms_url: str | None,
    source_license: str | None,
    cost_model: str | None,
    rate_limit: str | None,
    retention_rule: str | None,
    attribution_requirement: str | None,
    redistribution_rights: str | None,
    next_review_at: datetime | None,
    automated_monitoring_allowed: bool,
) -> str:
    """Apply one review decision to a scoped registry entry without retrieval."""
    decision = {
        "terms_url": terms_url,
        "source_license": source_license,
        "cost_model": cost_model,
        "rate_limit": rate_limit,
        "retention_rule": retention_rule,
        "attribution_requirement": attribution_requirement,
        "redistribution_rights": redistribution_rights,
    }
    if approval_status == "approved":
        missing = [field for field in APPROVAL_FIELDS if not decision[field]]
        if missing:
            raise ValueError(f"approved source reviews require: {', '.join(missing)}")
        if not terms_url.startswith("https://"):
            raise ValueError("terms URL must use HTTPS")
    elif automated_monitoring_allowed:
        raise ValueError("automated monitoring can be enabled only for an approved source")
    if automated_monitoring_allowed and permitted_use == "none":
        raise ValueError("automated monitoring requires a permitted source use")
    if permitted_use in {"private_retention", "public_copy"} and approval_status != "approved":
        raise ValueError("private retention and public copies require an approved source")
    if approval_status in {"rejected", "retired"} and permitted_use != "none":
        raise ValueError("rejected or retired sources must have no permitted use")

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
        if source["approval_status"] == "retired":
            raise ValueError("a retired source cannot be reactivated; register a replacement for fresh review")

        connection.execute(
            text(
                "UPDATE authority_source_registry "
                "SET terms_url = COALESCE(:terms_url, terms_url), "
                "source_license = COALESCE(:source_license, source_license), "
                "cost_model = COALESCE(:cost_model, cost_model), "
                "rate_limit = COALESCE(:rate_limit, rate_limit), "
                "retention_rule = COALESCE(:retention_rule, retention_rule), "
                "attribution_requirement = COALESCE(:attribution_requirement, attribution_requirement), "
                "redistribution_rights = COALESCE(:redistribution_rights, redistribution_rights), "
                "approval_status = :approval_status, "
                "reviewer_reference = :reviewer_reference, reviewed_at = :reviewed_at, "
                "review_notes = :review_notes, next_review_at = :next_review_at, "
                "automated_monitoring_allowed = :automated_monitoring_allowed, "
                "permitted_use = :permitted_use, "
                "permitted_use_reviewer_reference = :permitted_use_reviewer_reference, "
                "permitted_use_reviewed_at = :permitted_use_reviewed_at, "
                "permitted_use_notes = :permitted_use_notes "
                "WHERE id = :source_id"
            ),
            {
                **decision,
                "approval_status": approval_status,
                "permitted_use": permitted_use,
                "permitted_use_reviewer_reference": reviewer_reference if permitted_use != "none" else None,
                "permitted_use_reviewed_at": reviewed_at if permitted_use != "none" else None,
                "permitted_use_notes": review_notes if permitted_use != "none" else None,
                "reviewer_reference": reviewer_reference,
                "reviewed_at": reviewed_at,
                "review_notes": review_notes,
                "next_review_at": next_review_at,
                "automated_monitoring_allowed": automated_monitoring_allowed,
                "source_id": source["id"],
            },
        )
    return str(source["id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a source-review decision without retrieving the source.")
    parser.add_argument("--organization-slug", required=True)
    parser.add_argument("--publication-slug", required=True)
    parser.add_argument("--authority-slug", required=True)
    parser.add_argument("--source-slug", required=True)
    parser.add_argument("--approval-status", required=True, choices=APPROVAL_STATUSES)
    parser.add_argument(
        "--permitted-use",
        required=True,
        choices=PERMITTED_USES,
        help="direct_link_manual_check permits links and human checks only; it does not permit retention.",
    )
    parser.add_argument("--reviewer-reference", required=True, help="Operator identifier; do not use an address or voter data.")
    parser.add_argument("--reviewed-at", type=parse_utc_datetime, default=datetime.now(timezone.utc))
    parser.add_argument("--review-notes", help="Do not include PII, voter data, or private storage paths.")
    parser.add_argument("--terms-url")
    parser.add_argument("--source-license")
    parser.add_argument("--cost-model")
    parser.add_argument("--rate-limit")
    parser.add_argument("--retention-rule")
    parser.add_argument("--attribution-requirement")
    parser.add_argument("--redistribution-rights")
    parser.add_argument("--next-review-at", type=parse_utc_datetime)
    parser.add_argument("--automated-monitoring-allowed", action="store_true")
    arguments = parser.parse_args()

    source_id = review_source(
        engine=get_engine(),
        organization_slug=arguments.organization_slug,
        publication_slug=arguments.publication_slug,
        authority_slug=arguments.authority_slug,
        source_slug=arguments.source_slug,
        approval_status=arguments.approval_status,
        permitted_use=arguments.permitted_use,
        reviewer_reference=arguments.reviewer_reference,
        reviewed_at=arguments.reviewed_at,
        review_notes=arguments.review_notes,
        terms_url=arguments.terms_url,
        source_license=arguments.source_license,
        cost_model=arguments.cost_model,
        rate_limit=arguments.rate_limit,
        retention_rule=arguments.retention_rule,
        attribution_requirement=arguments.attribution_requirement,
        redistribution_rights=arguments.redistribution_rights,
        next_review_at=arguments.next_review_at,
        automated_monitoring_allowed=arguments.automated_monitoring_allowed,
    )
    print(f"Source review recorded: {source_id}")


if __name__ == "__main__":
    main()
