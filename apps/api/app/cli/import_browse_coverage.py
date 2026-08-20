"""Import a pinned Census ZCTA population-by-county calculation as draft evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID

from sqlalchemy import text

from app.database import get_engine
from app.document_storage import document_store_from_environment


SHA256 = re.compile(r"^[0-9a-f]{64}$")
USER_AGENT = "BallotApp browse coverage importer/1"
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


def read_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1:
        raise ValueError("browse coverage manifest must use schemaVersion 1")
    for section in ("zcta", "population"):
        source = manifest.get(section)
        if not isinstance(source, dict) or not str(source.get("endpoint", "")).startswith("https://"):
            raise ValueError(f"browse coverage manifest requires an HTTPS {section} source")
        for key, value in source.items():
            if key.lower().endswith("sha256") and not SHA256.fullmatch(str(value)):
                raise ValueError(f"browse coverage manifest has an invalid {section} checksum")
    targets = manifest.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("browse coverage manifest requires target counties")
    if [target.get("rank") for target in targets] != list(range(1, len(targets) + 1)):
        raise ValueError("browse coverage targets must have consecutive ranks")
    return manifest


def get_exact(url: str, parameters: dict[str, str], expected_sha256: str) -> tuple[bytes, str]:
    request_url = f"{url}?{urlencode(parameters)}"
    request = Request(request_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - manifest validates HTTPS
        content = response.read(MAX_RESPONSE_BYTES + 1)
    _verify_content(content, expected_sha256)
    return content, request_url


def post_exact(
    url: str,
    parameters: dict[str, str],
    *,
    expected_body_sha256: str,
    expected_response_sha256: str,
) -> bytes:
    body = urlencode(parameters).encode()
    if hashlib.sha256(body).hexdigest() != expected_body_sha256:
        raise ValueError("Census block request body no longer matches the reviewed manifest")
    request = Request(
        url,
        data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=60) as response:  # noqa: S310 - manifest validates HTTPS
        content = response.read(MAX_RESPONSE_BYTES + 1)
    _verify_content(content, expected_response_sha256)
    return content


def _verify_content(content: bytes, expected_sha256: str) -> None:
    if len(content) > MAX_RESPONSE_BYTES:
        raise ValueError("Census response exceeds the 10 MiB safety limit")
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"Census response checksum mismatch; received {actual}")


def calculate(manifest: dict[str, Any]) -> tuple[bytes, str, bytes, dict[str, Any], Counter[str]]:
    zcta = manifest["zcta"]
    zcta_content, zcta_request_url = get_exact(zcta["endpoint"], zcta["parameters"], zcta["responseSha256"])
    zcta_data = json.loads(zcta_content)
    features = zcta_data.get("features", [])
    if len(features) != 1 or str(features[0].get("attributes", {}).get("ZCTA5")) != zcta["query"]:
        raise ValueError("Census ZCTA response did not contain exactly the requested area")
    geometry = features[0].get("geometry")
    rings = geometry.get("rings") if isinstance(geometry, dict) else None
    if not isinstance(rings, list) or not rings:
        raise ValueError("Census ZCTA response did not contain polygon rings")

    population = manifest["population"]
    block_parameters = dict(population["parameters"])
    block_parameters["geometry"] = json.dumps(geometry, separators=(",", ":"))
    block_content = post_exact(
        population["endpoint"],
        block_parameters,
        expected_body_sha256=population["requestBodySha256"],
        expected_response_sha256=population["responseSha256"],
    )
    block_data = json.loads(block_content)
    block_features = block_data.get("features", [])
    if block_data.get("exceededTransferLimit") or len(block_features) != population["expectedBlockCount"]:
        raise ValueError("Census block response is incomplete or has an unexpected feature count")
    totals: Counter[str] = Counter()
    for feature in block_features:
        attributes = feature.get("attributes", {})
        if attributes.get("STATE") != "48":
            raise ValueError("Census block response unexpectedly included a non-Texas block")
        totals[str(attributes["COUNTY"])] += int(attributes.get("POP100") or 0)
    if sum(totals.values()) != population["expectedTotalPopulation"]:
        raise ValueError("Census block population total no longer matches the reviewed manifest")
    expected = {target["countyFips"]: target["expectedPopulation"] for target in manifest["targets"]}
    if dict(totals) != expected:
        raise ValueError("Census county population distribution no longer matches the reviewed manifest")
    return zcta_content, zcta_request_url, block_content, geometry, totals


def _document_id(connection: Any, *, source: dict[str, Any], title: str, source_url: str, stored: Any) -> UUID:
    return connection.execute(
        text(
            "WITH inserted AS (INSERT INTO documents "
            "(id, publication_id, election_authority_id, authority_source_registry_id, source_type, title, "
            "publisher_name, source_url, storage_key, checksum_sha256, retrieved_at, is_authoritative, "
            "artifact_retention, public_access_level, content_length_bytes) "
            "VALUES (gen_random_uuid(), :publication_id, :publisher_authority_id, :registry_id, "
            "'official_document', :title, 'United States Census Bureau', :source_url, :storage_key, :checksum, "
            ":retrieved_at, FALSE, 'retained', 'metadata_only', :content_length) "
            "ON CONFLICT (publication_id, checksum_sha256) DO NOTHING RETURNING id) "
            "SELECT id FROM inserted UNION ALL SELECT id FROM documents "
            "WHERE publication_id = :publication_id AND checksum_sha256 = :checksum LIMIT 1"
        ),
        {
            **source,
            "title": title,
            "source_url": source_url,
            "storage_key": stored.storage_key,
            "checksum": stored.checksum_sha256,
            "retrieved_at": datetime.now(UTC),
            "content_length": stored.content_length_bytes,
        },
    ).scalar_one()


def apply_calculation(
    manifest: dict[str, Any], zcta_content: bytes, zcta_request_url: str,
    block_content: bytes, geometry: dict[str, Any], totals: Counter[str],
) -> None:
    store = document_store_from_environment()
    with get_engine().begin() as connection:
        sources = connection.execute(
            text(
                "SELECT publications.id AS publication_id, publisher.id AS publisher_authority_id, "
                "registry.id AS registry_id, registry.slug, registry.source_url, "
                "registry.approval_status, registry.permitted_use "
                "FROM organizations JOIN publications ON publications.organization_id = organizations.id "
                "JOIN election_authorities publisher ON publisher.publication_id = publications.id "
                "JOIN authority_source_registry registry ON registry.authority_id = publisher.id "
                "WHERE organizations.slug = :organization_slug AND publications.slug = :publication_slug "
                "AND publisher.slug = :publisher_slug AND registry.slug IN (:zcta_slug, :population_slug)"
            ),
            {
                "organization_slug": manifest["organizationSlug"],
                "publication_slug": manifest["publicationSlug"],
                "publisher_slug": manifest["publisherSlug"],
                "zcta_slug": manifest["zcta"]["sourceSlug"],
                "population_slug": manifest["population"]["sourceSlug"],
            },
        ).mappings().all()
        by_slug = {source["slug"]: source for source in sources}
        if set(by_slug) != {manifest["zcta"]["sourceSlug"], manifest["population"]["sourceSlug"]}:
            raise ValueError("reviewed Census source registry entries were not found")
        unapproved = [
            f"{source['slug']} ({source['approval_status']}/{source['permitted_use']})"
            for source in sources
            if source["approval_status"] != "approved"
            or source["permitted_use"] not in {"private_retention", "public_copy"}
        ]
        if unapproved:
            raise ValueError(
                "Census browse sources require approved private retention before import: "
                + ", ".join(unapproved)
            )
        zcta_source = by_slug[manifest["zcta"]["sourceSlug"]]
        population_source = by_slug[manifest["population"]["sourceSlug"]]
        if not manifest["zcta"]["endpoint"].startswith(zcta_source["source_url"]):
            raise ValueError("ZCTA endpoint does not match its reviewed registry source")
        if not manifest["population"]["endpoint"].startswith(population_source["source_url"]):
            raise ValueError("population endpoint does not match its reviewed registry source")

        zcta_stored = store.put_bytes(zcta_content)
        block_stored = store.put_bytes(block_content)
        zcta_document_id = _document_id(
            connection, source=zcta_source, title="Census ZCTA 76522 pinned response",
            source_url=zcta_request_url, stored=zcta_stored,
        )
        block_document_id = _document_id(
            connection, source=population_source, title="Census 2020 blocks within ZCTA 76522 pinned response",
            source_url=manifest["population"]["endpoint"], stored=block_stored,
        )
        geojson = json.dumps({"type": "MultiPolygon", "coordinates": [geometry["rings"]]}, separators=(",", ":"))
        geometry_checksum = hashlib.sha256(geojson.encode()).hexdigest()
        browse_area_id = connection.execute(
            text(
                "WITH inserted AS (INSERT INTO browse_areas "
                "(id, publication_id, area_type, query_key, label, source_document_id, source_vintage, "
                "geometry_checksum_sha256, status, boundary) "
                "VALUES (gen_random_uuid(), :publication_id, 'zip', :query_key, :label, :document_id, "
                ":vintage, :checksum, 'draft', ST_Multi(ST_CollectionExtract(ST_MakeValid(" 
                "ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)), 3))) "
                "ON CONFLICT (publication_id, area_type, query_key, source_vintage) DO NOTHING RETURNING id) "
                "SELECT id FROM inserted UNION ALL SELECT id FROM browse_areas "
                "WHERE publication_id = :publication_id AND area_type = 'zip' AND query_key = :query_key "
                "AND source_vintage = :vintage LIMIT 1"
            ),
            {
                "publication_id": zcta_source["publication_id"], "query_key": manifest["zcta"]["query"],
                "label": f"Census ZCTA {manifest['zcta']['query']}", "document_id": zcta_document_id,
                "vintage": manifest["zcta"]["sourceVintage"], "checksum": geometry_checksum, "geojson": geojson,
            },
        ).scalar_one()
        stored_area = connection.execute(
            text(
                "SELECT source_document_id, geometry_checksum_sha256 FROM browse_areas WHERE id = :id"
            ),
            {"id": browse_area_id},
        ).mappings().one()
        if stored_area["source_document_id"] != zcta_document_id or stored_area["geometry_checksum_sha256"] != geometry_checksum:
            raise ValueError("existing browse area does not match the pinned source document and geometry")

        denominator = sum(totals.values())
        for target in manifest["targets"]:
            authority_id = connection.execute(
                text(
                    "SELECT id FROM election_authorities WHERE publication_id = :publication_id AND slug = :slug"
                ),
                {"publication_id": zcta_source["publication_id"], "slug": target["authoritySlug"]},
            ).scalar_one()
            area_id = connection.execute(
                text(
                    "WITH inserted AS (INSERT INTO geographic_areas "
                    "(id, authority_id, slug, name, area_type, external_identifier, status) "
                    "VALUES (gen_random_uuid(), :authority_id, :slug, :name, 'county', :fips, 'draft') "
                    "ON CONFLICT (authority_id, slug) DO NOTHING RETURNING id) "
                    "SELECT id FROM inserted UNION ALL SELECT id FROM geographic_areas "
                    "WHERE authority_id = :authority_id AND slug = :slug LIMIT 1"
                ),
                {
                    "authority_id": authority_id, "slug": f"county-{target['countyFips']}",
                    "name": target["name"], "fips": target["countyFips"],
                },
            ).scalar_one()
            numerator = totals[target["countyFips"]]
            estimate_id = connection.execute(
                text(
                    "WITH inserted AS (INSERT INTO browse_coverage_estimates "
                    "(id, publication_id, browse_area_id, target_kind, target_geographic_area_id, "
                    "target_authority_id, rank, estimated_share_percent, coverage_basis, numerator, "
                    "denominator, methodology, calculation_version, calculated_at, status) "
                    "VALUES (gen_random_uuid(), :publication_id, :browse_area_id, 'geographic_area', :area_id, "
                    ":authority_id, :rank, :percent, 'residential_population_estimate', :numerator, :denominator, "
                    ":methodology, :version, CURRENT_TIMESTAMP, 'draft') "
                    "ON CONFLICT DO NOTHING RETURNING id) SELECT id FROM inserted UNION ALL "
                    "SELECT id FROM browse_coverage_estimates WHERE browse_area_id = :browse_area_id "
                    "AND target_kind = 'geographic_area' AND target_geographic_area_id = :area_id LIMIT 1"
                ),
                {
                    "publication_id": zcta_source["publication_id"], "browse_area_id": browse_area_id,
                    "area_id": area_id, "authority_id": authority_id, "rank": target["rank"],
                    "percent": round(numerator * 100 / denominator, 4), "numerator": numerator,
                    "denominator": denominator,
                    "methodology": "Sum Census 2020 POP100 for blocks spatially contained by the ZCTA, grouped by county FIPS.",
                    "version": manifest["methodologyVersion"],
                },
            ).scalar_one()
            stored_estimate = connection.execute(
                text(
                    "SELECT rank, estimated_share_percent, numerator, denominator, calculation_version "
                    "FROM browse_coverage_estimates WHERE id = :id"
                ),
                {"id": estimate_id},
            ).mappings().one()
            expected_percent = round(numerator * 100 / denominator, 4)
            if (
                stored_estimate["rank"] != target["rank"]
                or abs(float(stored_estimate["estimated_share_percent"]) - expected_percent) > 0.00005
                or stored_estimate["numerator"] != numerator
                or stored_estimate["denominator"] != denominator
                or stored_estimate["calculation_version"] != manifest["methodologyVersion"]
            ):
                raise ValueError("existing browse coverage estimate does not match the pinned calculation")
            for document_id, role in ((zcta_document_id, "browse_boundary"), (block_document_id, "population")):
                evidence_exists = connection.execute(
                    text(
                        "SELECT 1 FROM browse_coverage_evidence "
                        "WHERE coverage_estimate_id = :estimate_id AND source_document_id = :document_id"
                    ),
                    {"estimate_id": estimate_id, "document_id": document_id},
                ).scalar_one_or_none()
                if evidence_exists is None:
                    connection.execute(
                        text(
                            "INSERT INTO browse_coverage_evidence "
                            "(coverage_estimate_id, source_document_id, publication_id, evidence_role) "
                            "VALUES (:estimate_id, :document_id, :publication_id, :role)"
                        ),
                        {
                            "estimate_id": estimate_id, "document_id": document_id,
                            "publication_id": zcta_source["publication_id"], "role": role,
                        },
                    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate or import pinned Census browse coverage evidence.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    manifest = read_manifest(arguments.manifest)
    zcta_content, zcta_url, block_content, geometry, totals = calculate(manifest)
    denominator = sum(totals.values())
    for target in manifest["targets"]:
        numerator = totals[target["countyFips"]]
        print(f"{target['name']}: {numerator}/{denominator} ({numerator * 100 / denominator:.2f}%)")
    if arguments.apply:
        apply_calculation(manifest, zcta_content, zcta_url, block_content, geometry, totals)
        print("Imported as draft browse coverage evidence")
    else:
        print("Validated pinned Census browse coverage calculation")


if __name__ == "__main__":
    main()
