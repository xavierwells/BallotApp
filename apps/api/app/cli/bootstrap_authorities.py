"""Load an authority/source manifest without retrieving external content.

Usage from ``apps/api`` after migrations have run:
``python -m app.cli.bootstrap_authorities``
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.database import get_engine


MANIFEST_RELATIVE_PATH = Path("data") / "authorities" / "copperas-cove-pilot.json"


def default_manifest_path() -> Path:
    """Locate the manifest in a checkout or at the Compose-mounted path.

    The API image deliberately contains only API code. Compose provides the
    editable pilot manifest as a read-only mount, while a source checkout has
    it at the repository root.
    """
    configured_path = os.getenv("AUTHORITY_MANIFEST_PATH")
    if configured_path:
        return Path(configured_path)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / MANIFEST_RELATIVE_PATH
        if candidate.is_file():
            return candidate
    return Path("/app") / MANIFEST_RELATIVE_PATH


DEFAULT_MANIFEST = default_manifest_path()
ALLOWED_AUTHORITY_TYPES = {
    "municipality",
    "county",
    "school_district",
    "state",
    "special_district",
    "other",
}
ALLOWED_SOURCE_CATEGORIES = {
    "election_information",
    "notices",
    "ballots",
    "results",
    "candidate_filings",
    "boundaries",
    "other",
}
ALLOWED_MONITORING_CLASSES = {"active_ballot", "active_election", "reference", "disabled"}
ALLOWED_PERMITTED_USES = {"none", "direct_link_manual_check", "private_retention", "public_copy"}


def read_manifest(path: Path) -> dict[str, Any]:
    """Return a minimally validated, local bootstrap manifest."""
    with path.open(encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)

    if manifest.get("schemaVersion") != 1:
        raise ValueError("authority manifest must use schemaVersion 1")
    publication = manifest.get("publication")
    authorities = manifest.get("authorities")
    if not isinstance(publication, dict) or not isinstance(authorities, list):
        raise ValueError("authority manifest requires publication and authorities")
    required_publication_fields = {"organizationSlug", "organizationName", "slug", "name"}
    if any(not isinstance(publication.get(field), str) or not publication[field] for field in required_publication_fields):
        raise ValueError("authority manifest has incomplete publication metadata")

    for authority in authorities:
        if not isinstance(authority, dict):
            raise ValueError("each authority must be an object")
        if authority.get("authorityType") not in ALLOWED_AUTHORITY_TYPES:
            raise ValueError(f"unsupported authority type: {authority.get('authorityType')!r}")
        if not str(authority.get("officialWebsiteUrl", "")).startswith("https://"):
            raise ValueError("authority websites must use HTTPS")
        sources = authority.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError("each authority needs at least one source")
        for source in sources:
            if source.get("sourceCategory") not in ALLOWED_SOURCE_CATEGORIES:
                raise ValueError(f"unsupported source category: {source.get('sourceCategory')!r}")
            if source.get("monitoringClass", "reference") not in ALLOWED_MONITORING_CLASSES:
                raise ValueError(f"unsupported monitoring class: {source.get('monitoringClass')!r}")
            if source.get("permittedUse", "none") not in ALLOWED_PERMITTED_USES:
                raise ValueError(f"unsupported permitted use: {source.get('permittedUse')!r}")
            if source.get("permittedUse", "none") not in {"none", "direct_link_manual_check"}:
                raise ValueError("bootstrap may grant only direct_link_manual_check; content rights require source review")
            if not str(source.get("sourceUrl", "")).startswith("https://"):
                raise ValueError("source URLs must use HTTPS")
            if source.get("approvalStatus", "pending_review") != "pending_review":
                raise ValueError("bootstrap sources must begin pending_review")
    return manifest


def bootstrap(manifest: dict[str, Any]) -> tuple[int, int]:
    """Upsert authorities and insert only new pending-review source entries."""
    publication = manifest["publication"]
    authority_count = 0
    source_count = 0

    with get_engine().begin() as connection:
        organization_id = connection.execute(
            text(
                "INSERT INTO organizations (id, slug, name) "
                "VALUES (gen_random_uuid(), :slug, :name) "
                "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id"
            ),
            {"slug": publication["organizationSlug"], "name": publication["organizationName"]},
        ).scalar_one()
        publication_id = connection.execute(
            text(
                "INSERT INTO publications (id, organization_id, slug, name) "
                "VALUES (gen_random_uuid(), :organization_id, :slug, :name) "
                "ON CONFLICT (organization_id, slug) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id"
            ),
            {
                "organization_id": organization_id,
                "slug": publication["slug"],
                "name": publication["name"],
            },
        ).scalar_one()

        for authority in manifest["authorities"]:
            authority_id = connection.execute(
                text(
                    "INSERT INTO election_authorities "
                    "(id, publication_id, slug, name, authority_type, official_website_url, status) "
                    "VALUES (gen_random_uuid(), :publication_id, :slug, :name, :authority_type, :website, 'active') "
                    "ON CONFLICT (publication_id, slug) DO UPDATE SET "
                    "name = EXCLUDED.name, authority_type = EXCLUDED.authority_type, "
                    "official_website_url = EXCLUDED.official_website_url "
                    "RETURNING id"
                ),
                {
                    "publication_id": publication_id,
                    "slug": authority["slug"],
                    "name": authority["name"],
                    "authority_type": authority["authorityType"],
                    "website": authority["officialWebsiteUrl"],
                },
            ).scalar_one()
            authority_count += 1
            for source in authority["sources"]:
                existing = connection.execute(
                    text(
                        "SELECT id, source_url, approval_status, permitted_use FROM authority_source_registry "
                        "WHERE authority_id = :authority_id AND slug = :slug"
                    ),
                    {"authority_id": authority_id, "slug": source["slug"]},
                ).mappings().one_or_none()
                if existing is not None:
                    if existing["source_url"] != source["sourceUrl"]:
                        raise RuntimeError(
                            f"source {authority['slug']}/{source['slug']} has changed; "
                            "retire it and register a replacement for fresh review"
                        )
                    requested_use = source.get("permittedUse", "none")
                    if existing["permitted_use"] == "none" and requested_use == "direct_link_manual_check":
                        connection.execute(
                            text(
                                "UPDATE authority_source_registry SET permitted_use = 'direct_link_manual_check', "
                                "permitted_use_reviewer_reference = 'initial-launch-policy', "
                                "permitted_use_reviewed_at = CURRENT_TIMESTAMP, "
                                "permitted_use_notes = 'Initial launch: direct links and manual checks only; no content retention or automation.' "
                                "WHERE id = :source_id"
                            ),
                            {"source_id": existing["id"]},
                        )
                    elif (
                        requested_use == "direct_link_manual_check"
                        and existing["permitted_use"] in {"private_retention", "public_copy"}
                    ):
                        # A recorded source review may broaden bootstrap's
                        # minimum scope. Never downgrade that reviewed choice.
                        pass
                    elif existing["permitted_use"] != requested_use:
                        raise RuntimeError(
                            f"source {authority['slug']}/{source['slug']} use scope has changed; "
                            "record a source review rather than changing scope through bootstrap"
                        )
                    continue
                connection.execute(
                    text(
                        "INSERT INTO authority_source_registry "
                        "(id, authority_id, slug, name, source_url, source_category, monitoring_class, approval_status, "
                        "permitted_use, permitted_use_reviewer_reference, permitted_use_reviewed_at, permitted_use_notes) "
                        "VALUES (gen_random_uuid(), :authority_id, :slug, :name, :source_url, :source_category, "
                        ":monitoring_class, 'pending_review', :permitted_use, :permitted_use_reviewer_reference, "
                        "CASE WHEN :permitted_use = 'none' THEN NULL ELSE CURRENT_TIMESTAMP END, :permitted_use_notes)"
                    ),
                    {
                        "authority_id": authority_id,
                        "slug": source["slug"],
                        "name": source["name"],
                        "source_url": source["sourceUrl"],
                        "source_category": source["sourceCategory"],
                        "monitoring_class": source.get("monitoringClass", "reference"),
                        "permitted_use": source.get("permittedUse", "none"),
                        "permitted_use_reviewer_reference": (
                            "initial-launch-policy" if source.get("permittedUse", "none") != "none" else None
                        ),
                        "permitted_use_notes": (
                            "Initial launch: direct links and manual checks only; no content retention or automation."
                            if source.get("permittedUse", "none") != "none"
                            else None
                        ),
                    },
                )
                source_count += 1
    return authority_count, source_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the local authority/source registry.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    arguments = parser.parse_args()
    manifest = read_manifest(arguments.manifest)
    authority_count, source_count = bootstrap(manifest)
    print(f"Registry synchronized: {authority_count} authorities examined; {source_count} pending-review sources added.")


if __name__ == "__main__":
    main()
