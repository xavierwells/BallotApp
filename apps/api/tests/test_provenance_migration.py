import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError

from app.database import sqlalchemy_database_url


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is required for PostgreSQL migration integration tests",
)


def alembic_config() -> Config:
    project_root = Path(__file__).resolve().parents[1]
    return Config(str(project_root / "alembic.ini"))


def test_provenance_core_upgrades_a_fresh_postgresql_database(monkeypatch: pytest.MonkeyPatch) -> None:
    assert TEST_DATABASE_URL is not None
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    command.upgrade(alembic_config(), "head")

    engine = create_engine(sqlalchemy_database_url())
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename IN "
                    "('organizations', 'publications', 'documents', 'source_claims', "
                    "'verification_events', 'elections', 'ballot_versions', 'ballot_items', "
                    "'offices', 'races', 'candidates', 'propositions', "
                    "'election_authorities', 'authority_source_registry')"
                )
            )
        }
        claim_statuses = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT enumlabel FROM pg_enum "
                    "WHERE enumtypid = 'editorial_status'::regtype"
                )
            )
        }
        trigger_names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE NOT tgisinternal AND tgname IN "
                    "('documents_immutable', 'verification_events_immutable', "
                    "'source_claims_published_immutable', "
                    "'source_claims_require_publication_event')"
                )
            )
        }
        document_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'documents' "
                    "AND column_name IN ('artifact_retention', 'public_access_level', 'content_length_bytes')"
                )
            )
        }

    assert len(tables) == 14
    assert {"draft", "verified", "published", "retracted", "superseded"} <= claim_statuses
    assert len(trigger_names) == 4
    assert document_columns == {"artifact_retention", "public_access_level", "content_length_bytes"}

    # A second invocation proves the command is safe for an already-current database.
    command.upgrade(alembic_config(), "head")

    test_suffix = uuid4().hex[:12]
    organization_id = str(uuid4())
    publication_id = str(uuid4())
    document_id = str(uuid4())
    authority_id = str(uuid4())
    registry_entry_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO organizations (id, slug, name) "
                "VALUES (:id, :slug, 'Test Organization')"
            ),
            {"id": organization_id, "slug": f"test-organization-{test_suffix}"},
        )
        connection.execute(
            text(
                "INSERT INTO publications (id, organization_id, slug, name) "
                "VALUES (:id, :organization_id, :slug, 'Test Publication')"
            ),
            {
                "id": publication_id,
                "organization_id": organization_id,
                "slug": f"test-publication-{test_suffix}",
            },
        )
        connection.execute(
            text(
                "INSERT INTO election_authorities "
                "(id, publication_id, slug, name, authority_type, official_website_url, status) "
                "VALUES (:id, :publication_id, :slug, 'Test County', 'county', "
                "'https://example.test/elections', 'active')"
            ),
            {
                "id": authority_id,
                "publication_id": publication_id,
                "slug": f"test-county-{test_suffix}",
            },
        )
        connection.execute(
            text(
                "INSERT INTO authority_source_registry "
                "(id, authority_id, slug, name, source_url, source_category) "
                "VALUES (:id, :authority_id, 'elections', 'Elections', "
                "'https://example.test/elections', 'election_information')"
            ),
            {"id": registry_entry_id, "authority_id": authority_id},
        )
        connection.execute(
            text(
                "INSERT INTO documents "
                "(id, publication_id, source_type, title, publisher_name, source_url, checksum_sha256, retrieved_at) "
                "VALUES (:id, :publication_id, 'official_document', 'Test source', "
                "'Test authority', 'https://example.test/source', :checksum, CURRENT_TIMESTAMP)"
            ),
            {"id": document_id, "publication_id": publication_id, "checksum": "a" * 64},
        )

    with pytest.raises(DatabaseError, match="ck_authority_source_registry_approved_reviewed"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO authority_source_registry "
                    "(id, authority_id, slug, name, source_url, source_category, approval_status) "
                    "VALUES (:id, :authority_id, 'unreviewed-approved', 'Unreviewed', "
                    "'https://example.test/unreviewed', 'other', 'approved')"
                ),
                {"id": str(uuid4()), "authority_id": authority_id},
            )

    second_authority_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO election_authorities "
                "(id, publication_id, slug, name, authority_type, official_website_url, status) "
                "VALUES (:id, :publication_id, :slug, 'Other County', 'county', "
                "'https://example.test/other', 'active')"
            ),
            {
                "id": second_authority_id,
                "publication_id": publication_id,
                "slug": f"other-county-{test_suffix}",
            },
        )

    with pytest.raises(DatabaseError, match="fk_documents_registry_authority"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO documents "
                    "(id, publication_id, election_authority_id, authority_source_registry_id, source_type, "
                    "title, publisher_name, source_url, checksum_sha256, retrieved_at) "
                    "VALUES (:id, :publication_id, :authority_id, :registry_id, 'official_document', "
                    "'Mismatched source', 'Other County', 'https://example.test/elections', :checksum, CURRENT_TIMESTAMP)"
                ),
                {
                    "id": str(uuid4()),
                    "publication_id": publication_id,
                    "authority_id": second_authority_id,
                    "registry_id": registry_entry_id,
                    "checksum": "b" * 64,
                },
            )

    with pytest.raises(DatabaseError, match="linked verification event"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO source_claims "
                    "(id, publication_id, document_id, claim_type, editorial_status, subject_type, subject_id, "
                    "claim_text, last_verified_at, published_at) "
                    "VALUES (:id, :publication_id, :document_id, 'verified_fact', 'published', 'candidate', :subject_id, "
                    "'A test claim', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "id": str(uuid4()),
                    "publication_id": publication_id,
                    "document_id": document_id,
                    "subject_id": str(uuid4()),
                },
            )

    published_claim_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO source_claims "
                "(id, publication_id, document_id, claim_type, editorial_status, subject_type, subject_id, "
                "claim_text, last_verified_at, published_at) "
                "VALUES (:id, :publication_id, :document_id, 'verified_fact', 'published', 'candidate', :subject_id, "
                "'A verified test claim', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": published_claim_id,
                "publication_id": publication_id,
                "document_id": document_id,
                "subject_id": str(uuid4()),
            },
        )
        connection.execute(
            text(
                "INSERT INTO verification_events "
                "(id, publication_id, source_claim_id, action, target_type, target_id, actor_reference, actor_role) "
                "VALUES (:id, :publication_id, :source_claim_id, 'published', 'source_claim', :target_id, "
                "'test-publisher', 'publisher')"
            ),
            {
                "id": str(uuid4()),
                "publication_id": publication_id,
                "source_claim_id": published_claim_id,
                "target_id": published_claim_id,
            },
        )

    with pytest.raises(DatabaseError, match="published source claims are immutable"):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE source_claims SET claim_text = 'Changed' WHERE id = :id"),
                {"id": published_claim_id},
            )

    with pytest.raises(NotImplementedError, match="forward-only"):
        command.downgrade(alembic_config(), "base")
