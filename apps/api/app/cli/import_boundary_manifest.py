"""Validate or import each county slice in a pinned boundary manifest."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any

from app.boundary_import import download_exact_https
from app.cli.import_boundaries import import_boundaries


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def read_manifest(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)

    required = {
        "organizationSlug", "publicationSlug", "publisherSlug", "sourceSlug",
        "sourceUrl", "sha256", "title", "publisherName", "areaType",
        "sourceSrid", "identifierField", "nameField", "resolutionEligibility", "imports",
    }
    if manifest.get("schemaVersion") != 1 or not required <= manifest.keys():
        raise ValueError("boundary manifest is incomplete or uses an unsupported schema version")
    if manifest["resolutionEligibility"] != "reference_only":
        raise ValueError("pilot boundary manifests must remain reference_only")
    if not str(manifest["sourceUrl"]).startswith("https://"):
        raise ValueError("boundary manifest source URL must use HTTPS")
    if not SHA256_PATTERN.fullmatch(str(manifest["sha256"])):
        raise ValueError("boundary manifest requires a lowercase SHA-256")
    if not isinstance(manifest["sourceSrid"], int) or manifest["sourceSrid"] <= 0:
        raise ValueError("boundary manifest requires a positive integer source SRID")
    if not isinstance(manifest["imports"], list) or not manifest["imports"]:
        raise ValueError("boundary manifest requires at least one import")
    seen_subjects: set[str] = set()
    for item in manifest["imports"]:
        if not all(item.get(field) for field in ("subjectSlug", "filterField", "filterValue")):
            raise ValueError("each boundary import requires a subject and filter")
        if item["subjectSlug"] in seen_subjects:
            raise ValueError("boundary manifest repeats a subject authority")
        seen_subjects.add(item["subjectSlug"])
        if not isinstance(item.get("expectedFeatureCount"), int) or item["expectedFeatureCount"] <= 0:
            raise ValueError("each boundary import requires a positive expected feature count")
    return manifest


def arguments_for(manifest: dict[str, Any], item: dict[str, Any], *, apply: bool) -> SimpleNamespace:
    effective_date = manifest.get("effectiveDate")
    return SimpleNamespace(
        organization_slug=manifest["organizationSlug"],
        publication_slug=manifest["publicationSlug"],
        publisher_slug=manifest["publisherSlug"],
        subject_slug=item["subjectSlug"],
        source_slug=manifest["sourceSlug"],
        source_url=manifest["sourceUrl"],
        sha256=manifest["sha256"],
        title=manifest["title"],
        publisher_name=manifest["publisherName"],
        area_type=manifest["areaType"],
        source_srid=manifest["sourceSrid"],
        identifier_field=manifest["identifierField"],
        name_field=manifest["nameField"],
        filter_field=item["filterField"],
        filter_value=str(item["filterValue"]),
        effective_date=date.fromisoformat(effective_date) if effective_date else None,
        apply=apply,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run checksum-pinned reference boundary imports from a manifest.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    manifest = read_manifest(arguments.manifest)
    content = download_exact_https(manifest["sourceUrl"], manifest["sha256"])
    total = 0
    for item in manifest["imports"]:
        count = import_boundaries(arguments_for(manifest, item, apply=arguments.apply), content=content)
        if count != item["expectedFeatureCount"]:
            raise ValueError(
                f"{item['subjectSlug']} produced {count} features; "
                f"manifest expected {item['expectedFeatureCount']}"
            )
        total += count
        print(f"{item['subjectSlug']}: {count} feature(s)")
    action = "Imported as draft/reference" if arguments.apply else "Validated"
    print(f"{action}: {total} feature(s) across {len(manifest['imports'])} authorities")


if __name__ == "__main__":
    main()
