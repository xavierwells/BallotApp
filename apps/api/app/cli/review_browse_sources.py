"""Record one operator decision for every source in a browse calculation manifest."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from app.cli.import_browse_coverage import read_manifest
from app.cli.review_source import review_source
from app.database import get_engine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Approve the source set documented by one reviewed browse calculation manifest."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reviewer-reference", required=True, help="Stable operator ID; never voter data.")
    arguments = parser.parse_args()
    manifest = read_manifest(arguments.manifest)
    review = manifest.get("sourceReview")
    required = {
        "termsUrl", "sourceLicense", "costModel", "rateLimit", "retentionRule",
        "attributionRequirement", "redistributionRights", "permittedUse",
    }
    if not isinstance(review, dict) or not required <= review.keys():
        raise ValueError("browse manifest does not contain a complete source review decision")
    if review["permittedUse"] != "private_retention":
        raise ValueError("browse source-set review must remain private_retention")

    reviewed_at = datetime.now(UTC)
    engine = get_engine()
    source_ids: list[str] = []
    for section_name in ("zcta", "population"):
        section = manifest[section_name]
        source_ids.append(
            review_source(
                engine=engine,
                organization_slug=manifest["organizationSlug"],
                publication_slug=manifest["publicationSlug"],
                authority_slug=manifest["publisherSlug"],
                source_slug=section["sourceSlug"],
                approval_status="approved",
                permitted_use=review["permittedUse"],
                reviewer_reference=arguments.reviewer_reference,
                reviewed_at=reviewed_at,
                review_notes=section["reviewNotes"],
                terms_url=review["termsUrl"],
                source_license=review["sourceLicense"],
                cost_model=review["costModel"],
                rate_limit=review["rateLimit"],
                retention_rule=review["retentionRule"],
                attribution_requirement=review["attributionRequirement"],
                redistribution_rights=review["redistributionRights"],
                next_review_at=None,
                automated_monitoring_allowed=False,
            )
        )
    print(f"Browse source-set review recorded: {len(source_ids)} sources approved for private retention")


if __name__ == "__main__":
    main()
