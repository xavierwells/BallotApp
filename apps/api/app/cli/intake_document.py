"""Retain a manually supplied official document without retrieving a URL.

Usage from ``apps/api`` after a registry entry is present:
``python -m app.cli.intake_document --help``
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app.database import get_engine
from app.document_storage import document_store_from_environment


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 time and make a naive timestamp explicitly UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def intake_document(
    *,
    organization_slug: str,
    publication_slug: str,
    authority_slug: str,
    source_slug: str,
    file_path: Path,
    title: str,
    publisher_name: str,
    source_url: str,
    retrieved_at: datetime,
    document_published_at: datetime | None,
    public_access_level: str,
) -> str:
    """Store an artifact, then create its immutable document metadata row."""
    if not source_url.startswith("https://"):
        raise ValueError("source URL must use HTTPS")
    if not file_path.is_file():
        raise ValueError(f"document file does not exist: {file_path}")

    stored = document_store_from_environment().put_bytes(file_path.read_bytes())
    with get_engine().begin() as connection:
        registry_entry = connection.execute(
            text(
                "SELECT publication.id AS publication_id, election_authorities.id AS authority_id, "
                "authority_source_registry.id AS registry_id, authority_source_registry.permitted_use "
                "FROM publications "
                "JOIN election_authorities ON election_authorities.publication_id = publications.id "
                "JOIN authority_source_registry ON authority_source_registry.authority_id = election_authorities.id "
                "JOIN organizations ON organizations.id = publications.organization_id "
                "WHERE organizations.slug = :organization_slug AND publications.slug = :publication_slug "
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
        if registry_entry is None:
            raise ValueError("authority/source registry entry was not found")
        if registry_entry["permitted_use"] not in {"private_retention", "public_copy"}:
            raise ValueError("source use does not permit private document retention")
        if public_access_level == "public_copy" and registry_entry["permitted_use"] != "public_copy":
            raise ValueError("public_copy requires a source review that explicitly permits public copies")

        existing = connection.execute(
            text(
                "SELECT id FROM documents WHERE publication_id = :publication_id AND checksum_sha256 = :checksum"
            ),
            {"publication_id": registry_entry["publication_id"], "checksum": stored.checksum_sha256},
        ).scalar_one_or_none()
        if existing is not None:
            return str(existing)

        document_id = connection.execute(
            text(
                "INSERT INTO documents "
                "(id, publication_id, election_authority_id, authority_source_registry_id, source_type, title, "
                "publisher_name, source_url, storage_key, checksum_sha256, document_published_at, retrieved_at, "
                "is_authoritative, artifact_retention, public_access_level, content_length_bytes) "
                "VALUES (gen_random_uuid(), :publication_id, :authority_id, :registry_id, 'official_document', "
                ":title, :publisher_name, :source_url, :storage_key, :checksum, :document_published_at, :retrieved_at, "
                "TRUE, 'retained', :public_access_level, :content_length_bytes) RETURNING id"
            ),
            {
                "publication_id": registry_entry["publication_id"],
                "authority_id": registry_entry["authority_id"],
                "registry_id": registry_entry["registry_id"],
                "title": title,
                "publisher_name": publisher_name,
                "source_url": source_url,
                "storage_key": stored.storage_key,
                "checksum": stored.checksum_sha256,
                "document_published_at": document_published_at,
                "retrieved_at": retrieved_at,
                "public_access_level": public_access_level,
                "content_length_bytes": stored.content_length_bytes,
            },
        ).scalar_one()
    return str(document_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually retain an official source document.")
    parser.add_argument("--organization-slug", default="whats-on-my-ballot")
    parser.add_argument("--publication-slug", default="copperas-cove")
    parser.add_argument("--authority-slug", required=True)
    parser.add_argument("--source-slug", required=True)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--publisher-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--retrieved-at", type=parse_timestamp)
    parser.add_argument("--document-published-at", type=parse_timestamp)
    parser.add_argument("--public-access-level", choices=("metadata_only", "public_copy"), default="metadata_only")
    arguments = parser.parse_args()
    document_id = intake_document(
        organization_slug=arguments.organization_slug,
        publication_slug=arguments.publication_slug,
        authority_slug=arguments.authority_slug,
        source_slug=arguments.source_slug,
        file_path=arguments.file,
        title=arguments.title,
        publisher_name=arguments.publisher_name,
        source_url=arguments.source_url,
        retrieved_at=arguments.retrieved_at or datetime.now(UTC),
        document_published_at=arguments.document_published_at,
        public_access_level=arguments.public_access_level,
    )
    print(f"Document retained and registered: {document_id}")


if __name__ == "__main__":
    main()
