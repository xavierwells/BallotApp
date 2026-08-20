"""Promote one complete, pinned draft browse calculation after operator review."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import text

from app.cli.import_browse_coverage import read_manifest
from app.database import get_engine


def review_calculation(manifest: dict, reviewer_reference: str) -> int:
    with get_engine().begin() as connection:
        browse_area = connection.execute(
            text(
                "SELECT ba.id, ba.publication_id, ba.status, d.checksum_sha256 "
                "FROM organizations o JOIN publications p ON p.organization_id = o.id "
                "JOIN browse_areas ba ON ba.publication_id = p.id "
                "JOIN documents d ON d.id = ba.source_document_id "
                "WHERE o.slug = :organization_slug AND p.slug = :publication_slug "
                "AND ba.area_type = 'zip' AND ba.query_key = :query_key AND ba.source_vintage = :vintage"
            ),
            {
                "organization_slug": manifest["organizationSlug"],
                "publication_slug": manifest["publicationSlug"],
                "query_key": manifest["zcta"]["query"],
                "vintage": manifest["zcta"]["sourceVintage"],
            },
        ).mappings().one_or_none()
        if browse_area is None:
            raise ValueError("the pinned draft browse area has not been imported")
        if browse_area["checksum_sha256"] != manifest["zcta"]["responseSha256"]:
            raise ValueError("the imported browse area source checksum does not match the reviewed manifest")

        estimates = connection.execute(
            text(
                "SELECT e.id, e.status, e.rank, e.numerator, e.denominator, e.calculation_version, "
                "ga.external_identifier AS county_fips, ga.status AS geographic_area_status, "
                "COUNT(ev.source_document_id) AS evidence_count, "
                "COUNT(ev.source_document_id) FILTER (WHERE d.checksum_sha256 = :zcta_checksum) AS zcta_evidence, "
                "COUNT(ev.source_document_id) FILTER (WHERE d.checksum_sha256 = :population_checksum) AS population_evidence "
                "FROM browse_coverage_estimates e "
                "JOIN geographic_areas ga ON ga.id = e.target_geographic_area_id "
                "LEFT JOIN browse_coverage_evidence ev ON ev.coverage_estimate_id = e.id "
                "LEFT JOIN documents d ON d.id = ev.source_document_id "
                "WHERE e.browse_area_id = :browse_area_id AND e.target_kind = 'geographic_area' "
                "GROUP BY e.id, ga.external_identifier, ga.status ORDER BY e.rank"
            ),
            {
                "browse_area_id": browse_area["id"],
                "zcta_checksum": manifest["zcta"]["responseSha256"],
                "population_checksum": manifest["population"]["responseSha256"],
            },
        ).mappings().all()
        targets = {target["countyFips"]: target for target in manifest["targets"]}
        if len(estimates) != len(targets):
            raise ValueError("the imported calculation does not contain the complete reviewed target set")
        for estimate in estimates:
            target = targets.get(estimate["county_fips"])
            if target is None or (
                estimate["rank"] != target["rank"]
                or estimate["numerator"] != target["expectedPopulation"]
                or estimate["denominator"] != manifest["population"]["expectedTotalPopulation"]
                or estimate["calculation_version"] != manifest["methodologyVersion"]
                or estimate["evidence_count"] != 2
                or estimate["zcta_evidence"] != 1
                or estimate["population_evidence"] != 1
            ):
                raise ValueError("an imported coverage estimate or its evidence differs from the reviewed manifest")

        for estimate in estimates:
            if estimate["geographic_area_status"] == "draft":
                connection.execute(
                    text("UPDATE geographic_areas SET status = 'active' WHERE id = (SELECT target_geographic_area_id FROM browse_coverage_estimates WHERE id = :id)"),
                    {"id": estimate["id"]},
                )
            if estimate["status"] == "draft":
                connection.execute(
                    text(
                        "UPDATE browse_coverage_estimates SET status = 'verified', "
                        "verified_by_reference = :reviewer, verified_at = CURRENT_TIMESTAMP WHERE id = :id"
                    ),
                    {"id": estimate["id"], "reviewer": reviewer_reference},
                )
            elif estimate["status"] != "verified":
                raise ValueError("a coverage estimate is not reviewable")
        if browse_area["status"] == "draft":
            connection.execute(
                text(
                    "UPDATE browse_areas SET status = 'verified', verified_by_reference = :reviewer, "
                    "verified_at = CURRENT_TIMESTAMP WHERE id = :id"
                ),
                {"id": browse_area["id"], "reviewer": reviewer_reference},
            )
        elif browse_area["status"] != "verified":
            raise ValueError("the browse area is not reviewable")
    return len(estimates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and promote a pinned draft browse calculation.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reviewer-reference", required=True, help="Stable operator ID; never voter data.")
    arguments = parser.parse_args()
    count = review_calculation(read_manifest(arguments.manifest), arguments.reviewer_reference)
    print(f"Browse calculation verified: {count} ranked area matches promoted")


if __name__ == "__main__":
    main()
