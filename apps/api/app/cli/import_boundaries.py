"""Validate and optionally import a checksum-pinned shapefile as draft geometry."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
import re

from sqlalchemy import text

from app.boundary_import import download_exact_https, read_shapefile_zip
from app.database import get_engine
from app.document_storage import document_store_from_environment


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("boundary name cannot be converted to a stable slug")
    return slug[:120].rstrip("-")


def import_boundaries(arguments: argparse.Namespace) -> int:
    content = download_exact_https(arguments.source_url, arguments.sha256)
    features = read_shapefile_zip(
        content,
        identifier_field=arguments.identifier_field,
        name_field=arguments.name_field,
        filter_field=arguments.filter_field,
        filter_value=arguments.filter_value,
    )
    if not arguments.apply:
        return len(features)

    stored = document_store_from_environment().put_bytes(content)
    with get_engine().begin() as connection:
        source = connection.execute(
            text(
                "SELECT publications.id AS publication_id, publisher.id AS publisher_authority_id, "
                "subject.id AS subject_authority_id, registry.id AS registry_id, "
                "registry.approval_status, registry.permitted_use "
                "FROM organizations "
                "JOIN publications ON publications.organization_id = organizations.id "
                "JOIN election_authorities publisher ON publisher.publication_id = publications.id "
                "JOIN authority_source_registry registry ON registry.authority_id = publisher.id "
                "JOIN election_authorities subject ON subject.publication_id = publications.id "
                "WHERE organizations.slug = :organization_slug "
                "AND publications.slug = :publication_slug "
                "AND publisher.slug = :publisher_slug AND registry.slug = :source_slug "
                "AND subject.slug = :subject_slug"
            ),
            vars(arguments),
        ).mappings().one_or_none()
        if source is None:
            raise ValueError("publisher source or subject authority was not found in this publication")
        if source["approval_status"] != "approved":
            raise ValueError("boundary source registry entry must be approved before import")
        if source["permitted_use"] not in {"private_retention", "public_copy"}:
            raise ValueError("boundary source review does not permit retaining the source artifact")

        document_id = connection.execute(
            text(
                "INSERT INTO documents "
                "(id, publication_id, election_authority_id, authority_source_registry_id, source_type, "
                "title, publisher_name, source_url, storage_key, checksum_sha256, retrieved_at, "
                "is_authoritative, artifact_retention, public_access_level, content_length_bytes) "
                "VALUES (gen_random_uuid(), :publication_id, :publisher_authority_id, :registry_id, "
                "'official_document', :title, :publisher_name, :source_url, :storage_key, :checksum, "
                ":retrieved_at, FALSE, 'retained', 'metadata_only', :content_length) "
                "ON CONFLICT (publication_id, checksum_sha256) DO UPDATE "
                "SET checksum_sha256 = EXCLUDED.checksum_sha256 RETURNING id"
            ),
            {
                **source,
                "title": arguments.title,
                "publisher_name": arguments.publisher_name,
                "source_url": arguments.source_url,
                "storage_key": stored.storage_key,
                "checksum": stored.checksum_sha256,
                "retrieved_at": datetime.now(UTC),
                "content_length": stored.content_length_bytes,
            },
        ).scalar_one()
        dataset_id = connection.execute(
            text(
                "INSERT INTO boundary_datasets "
                "(id, publisher_authority_id, subject_authority_id, authority_source_registry_id, "
                "source_document_id, source_url, source_effective_date, checked_at, status) "
                "VALUES (gen_random_uuid(), :publisher_authority_id, :subject_authority_id, :registry_id, "
                ":document_id, :source_url, :effective_date, CURRENT_TIMESTAMP, 'registered') RETURNING id"
            ),
            {
                **source,
                "document_id": document_id,
                "source_url": arguments.source_url,
                "effective_date": arguments.effective_date,
            },
        ).scalar_one()

        for feature in features:
            area_id = connection.execute(
                text(
                    "INSERT INTO geographic_areas "
                    "(id, authority_id, slug, name, area_type, external_identifier, status) "
                    "VALUES (gen_random_uuid(), :authority_id, :slug, :name, :area_type, "
                    ":external_identifier, 'draft') "
                    "ON CONFLICT (authority_id, slug) DO UPDATE SET name = EXCLUDED.name "
                    "RETURNING id"
                ),
                {
                    "authority_id": source["subject_authority_id"],
                    "slug": slugify(f"{arguments.area_type}-{feature.external_identifier}"),
                    "name": feature.name,
                    "area_type": arguments.area_type,
                    "external_identifier": feature.external_identifier,
                },
            ).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO boundary_versions "
                    "(id, authority_id, geographic_area_id, boundary_dataset_id, effective_from, "
                    "geometry_checksum_sha256, status, boundary) "
                    "VALUES (gen_random_uuid(), :authority_id, :area_id, :dataset_id, :effective_date, "
                    ":checksum, 'draft', ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Transform(" 
                    "ST_SetSRID(ST_GeomFromGeoJSON(:geojson), :source_srid), 4326)), 3)))"
                ),
                {
                    "authority_id": source["subject_authority_id"],
                    "area_id": area_id,
                    "dataset_id": dataset_id,
                    "effective_date": arguments.effective_date,
                    "checksum": feature.geometry_checksum_sha256,
                    "geojson": feature.geojson,
                    "source_srid": arguments.source_srid,
                },
            )
    return len(features)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a pinned shapefile ZIP; --apply writes draft/reference records only."
    )
    parser.add_argument("--organization-slug", default="whats-on-my-ballot")
    parser.add_argument("--publication-slug", default="copperas-cove")
    parser.add_argument("--publisher-slug", required=True)
    parser.add_argument("--subject-slug", required=True)
    parser.add_argument("--source-slug", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--publisher-name", required=True)
    parser.add_argument("--area-type", required=True)
    parser.add_argument("--source-srid", type=int, required=True)
    parser.add_argument("--identifier-field", required=True)
    parser.add_argument("--name-field", required=True)
    parser.add_argument("--filter-field")
    parser.add_argument("--filter-value")
    parser.add_argument("--effective-date", type=date.fromisoformat)
    parser.add_argument("--apply", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    arguments = parser.parse_args()
    if bool(arguments.filter_field) != bool(arguments.filter_value):
        parser.error("--filter-field and --filter-value must be supplied together")
    imported = import_boundaries(arguments)
    action = "Imported as draft" if arguments.apply else "Validated (dry run)"
    print(f"{action}: {imported} boundary feature(s)")


if __name__ == "__main__":
    main()
