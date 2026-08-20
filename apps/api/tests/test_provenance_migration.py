import os
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError

from app.ballot_matching import (
    BallotMatcher,
    BallotMatchStatus,
    PostgresBallotRequirementRepository,
)
from app.boundary_resolution import (
    BoundaryResolutionStatus,
    BoundaryResolver,
    PostgisBoundaryRepository,
)
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
                    "'election_authorities', 'authority_source_registry', "
                    "'verification_cadence_policies', 'source_verification_checks', 'source_alerts', "
                    "'geographic_areas', 'boundary_datasets', 'boundary_versions', "
                    "'ballot_geographic_requirements', 'browse_areas', "
                    "'browse_coverage_estimates', 'browse_coverage_evidence')"
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
                    "'source_claims_require_publication_event', "
                    "'verification_cadence_policies_scope_valid', "
                    "'source_verification_checks_immutable', "
                    "'source_alerts_resolve_after_manual_unchanged_check', "
                    "'source_registry_schedule_after_check', "
                    "'source_alerts_open_after_source_check', "
                    "'boundary_datasets_final_immutable', "
                    "'boundary_versions_verified_immutable', "
                    "'ballot_area_requirements_final_immutable', "
                    "'ballot_versions_require_geography', "
                    "'ballot_items_final_immutable', "
                    "'ballot_versions_require_complete_content', "
                    "'browse_areas_final_immutable', 'browse_estimates_final_immutable', "
                    "'browse_evidence_final_immutable')"
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
        source_registry_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'authority_source_registry' "
                    "AND column_name IN ('monitoring_class', 'automated_monitoring_allowed', 'permitted_use', "
                    "'permitted_use_reviewer_reference', 'permitted_use_reviewed_at', 'permitted_use_notes')"
                )
            )
        }
        postgis_version = connection.execute(text("SELECT PostGIS_Version()")).scalar_one()
        boundary_geometry = connection.execute(
            text(
                "SELECT type, srid FROM geometry_columns "
                "WHERE f_table_schema = 'public' AND f_table_name = 'boundary_versions' "
                "AND f_geometry_column = 'boundary'"
            )
        ).mappings().one()
        browse_geometry = connection.execute(
            text(
                "SELECT type, srid FROM geometry_columns "
                "WHERE f_table_schema = 'public' AND f_table_name = 'browse_areas' "
                "AND f_geometry_column = 'boundary'"
            )
        ).mappings().one()

    assert len(tables) == 24
    assert {"draft", "verified", "published", "retracted", "superseded"} <= claim_statuses
    assert len(trigger_names) == 18
    assert postgis_version
    assert boundary_geometry == {"type": "MULTIPOLYGON", "srid": 4326}
    assert browse_geometry == {"type": "MULTIPOLYGON", "srid": 4326}
    assert document_columns == {"artifact_retention", "public_access_level", "content_length_bytes"}
    assert source_registry_columns == {
        "monitoring_class",
        "automated_monitoring_allowed",
        "permitted_use",
        "permitted_use_reviewer_reference",
        "permitted_use_reviewed_at",
        "permitted_use_notes",
    }

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
                "'https://example.test/elections', 'boundaries')"
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

    geographic_area_id = str(uuid4())
    boundary_dataset_id = str(uuid4())
    boundary_version_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO geographic_areas "
                "(id, authority_id, slug, name, area_type, status) "
                "VALUES (:id, :authority_id, 'synthetic-precinct', 'Synthetic Precinct', "
                "'voting_precinct', 'active')"
            ),
            {"id": geographic_area_id, "authority_id": authority_id},
        )
        connection.execute(
            text(
                "INSERT INTO boundary_datasets "
                "(id, publisher_authority_id, subject_authority_id, authority_source_registry_id, "
                "source_url, checked_at, status, "
                "reviewer_reference, reviewed_at) "
                "VALUES (:id, :authority_id, :authority_id, :registry_id, "
                "'https://example.test/boundaries', "
                "CURRENT_TIMESTAMP, 'imported', 'synthetic-test', CURRENT_TIMESTAMP)"
            ),
            {
                "id": boundary_dataset_id,
                "authority_id": authority_id,
                "registry_id": registry_entry_id,
            },
        )

        connection.execute(
            text(
                "INSERT INTO boundary_versions "
                "(id, authority_id, geographic_area_id, boundary_dataset_id, effective_from, "
                "geometry_checksum_sha256, status, verified_by_reference, verified_at, boundary) "
                "VALUES (:id, :authority_id, :area_id, :dataset_id, DATE '2026-01-01', :checksum, "
                "'verified', 'synthetic-test', CURRENT_TIMESTAMP, "
                "ST_GeomFromText('MULTIPOLYGON(((-97.91 31.10, -97.89 31.10, "
                "-97.89 31.12, -97.91 31.12, -97.91 31.10)))', 4326))"
            ),
            {
                "id": boundary_version_id,
                "authority_id": authority_id,
                "area_id": geographic_area_id,
                "dataset_id": boundary_dataset_id,
                "checksum": "c" * 64,
            },
        )
        contains_synthetic_point = connection.execute(
            text(
                "SELECT ST_Covers(boundary, ST_SetSRID(ST_Point(-97.90, 31.11), 4326)) "
                "FROM boundary_versions WHERE id = :id"
            ),
            {"id": boundary_version_id},
        ).scalar_one()

    assert contains_synthetic_point is True

    resolver = BoundaryResolver(PostgisBoundaryRepository(engine))
    interior_resolution = resolver.resolve(
        longitude=-97.90,
        latitude=31.11,
        effective_on=date(2026, 11, 3),
    )
    edge_resolution = resolver.resolve(
        longitude=-97.91,
        latitude=31.10,
        effective_on=date(2026, 11, 3),
    )
    assert interior_resolution.status is BoundaryResolutionStatus.MATCHED
    assert interior_resolution.memberships[0].boundary_version_id == UUID(boundary_version_id)
    assert edge_resolution.status is BoundaryResolutionStatus.AMBIGUOUS

    election_id = str(uuid4())
    ballot_version_id = str(uuid4())
    proposition_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO elections "
                "(id, publication_id, authority_name, jurisdiction_name, election_date, "
                "election_type, official_document_id) "
                "VALUES (:id, :publication_id, 'Test County', 'Synthetic Jurisdiction', "
                "DATE '2026-11-03', 'general', :document_id)"
            ),
            {
                "id": election_id,
                "publication_id": publication_id,
                "document_id": document_id,
            },
        )
        connection.execute(
            text(
                "INSERT INTO ballot_versions "
                "(id, publication_id, election_id, official_document_id, external_identifier, "
                "status, retrieved_at) "
                "VALUES (:id, :publication_id, :election_id, :document_id, 'synthetic-style', "
                "'draft', CURRENT_TIMESTAMP)"
            ),
            {
                "id": ballot_version_id,
                "publication_id": publication_id,
                "election_id": election_id,
                "document_id": document_id,
            },
        )
        connection.execute(
            text(
                "INSERT INTO ballot_geographic_requirements "
                "(ballot_version_id, publication_id, geographic_area_id, authority_id, "
                "source_document_id, verified_by_reference, verified_at) "
                "VALUES (:ballot_id, :publication_id, :area_id, :authority_id, "
                ":document_id, 'synthetic-test', CURRENT_TIMESTAMP)"
            ),
            {
                "ballot_id": ballot_version_id,
                "publication_id": publication_id,
                "area_id": geographic_area_id,
                "authority_id": authority_id,
                "document_id": document_id,
            },
        )
        connection.execute(
            text(
                "INSERT INTO propositions "
                "(id, publication_id, election_id, official_document_id, external_identifier, "
                "ballot_title, official_text, source_page) VALUES "
                "(:id, :publication_id, :election_id, :document_id, 'synthetic-proposition', "
                "'Synthetic Proposition', 'Synthetic official text.', '1')"
            ),
            {"id": proposition_id, "publication_id": publication_id,
             "election_id": election_id, "document_id": document_id},
        )
        connection.execute(
            text(
                "INSERT INTO ballot_items "
                "(id, publication_id, ballot_version_id, proposition_id, sequence, source_page) "
                "VALUES (gen_random_uuid(), :publication_id, :ballot_id, :proposition_id, 1, '1')"
            ),
            {"publication_id": publication_id, "ballot_id": ballot_version_id,
             "proposition_id": proposition_id},
        )
        for reviewer in ("synthetic-verifier-one", "synthetic-verifier-two"):
            connection.execute(
                text(
                    "INSERT INTO verification_events "
                    "(id, publication_id, action, target_type, target_id, actor_reference, actor_role) "
                    "VALUES (gen_random_uuid(), :publication_id, 'verified', 'ballot_version', "
                    ":ballot_id, :reviewer, 'verifier')"
                ),
                {"publication_id": publication_id, "ballot_id": ballot_version_id, "reviewer": reviewer},
            )
        connection.execute(
            text(
                "UPDATE ballot_versions SET status = 'published', published_at = CURRENT_TIMESTAMP "
                "WHERE id = :id"
            ),
            {"id": ballot_version_id},
        )

    ballot_match = BallotMatcher(PostgresBallotRequirementRepository(engine)).match(
        publication_id=UUID(publication_id),
        election_id=UUID(election_id),
        effective_on=date(2026, 11, 3),
        geographic_area_ids=frozenset({UUID(geographic_area_id)}),
    )
    assert ballot_match.status is BallotMatchStatus.MATCHED
    assert ballot_match.ballot_version_ids == (UUID(ballot_version_id),)

    one_review_ballot_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO ballot_versions (id,publication_id,election_id,official_document_id,external_identifier,status,retrieved_at) "
            "VALUES (:id,:p,:e,:d,'synthetic-one-review','draft',CURRENT_TIMESTAMP)"
        ), {"id": one_review_ballot_id, "p": publication_id, "e": election_id, "d": document_id})
        connection.execute(text(
            "INSERT INTO ballot_geographic_requirements (ballot_version_id,publication_id,geographic_area_id,authority_id,source_document_id,verified_by_reference,verified_at) "
            "VALUES (:b,:p,:a,:authority,:d,'synthetic-test',CURRENT_TIMESTAMP)"
        ), {"b": one_review_ballot_id, "p": publication_id, "a": geographic_area_id,
            "authority": authority_id, "d": document_id})
        connection.execute(text(
            "INSERT INTO ballot_items (id,publication_id,ballot_version_id,proposition_id,sequence,source_page) "
            "VALUES (gen_random_uuid(),:p,:b,:q,1,'1')"
        ), {"p": publication_id, "b": one_review_ballot_id, "q": proposition_id})
        connection.execute(text(
            "INSERT INTO verification_events (id,publication_id,action,target_type,target_id,actor_reference,actor_role) "
            "VALUES (gen_random_uuid(),:p,'verified','ballot_version',:b,'only-one-verifier','verifier')"
        ), {"p": publication_id, "b": one_review_ballot_id})

    with pytest.raises(DatabaseError, match="two distinct reviewers"):
        with engine.begin() as connection:
            connection.execute(text(
                "UPDATE ballot_versions SET status='published',published_at=CURRENT_TIMESTAMP WHERE id=:id"
            ), {"id": one_review_ballot_id})

    unmapped_ballot_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO ballot_versions "
                "(id, publication_id, election_id, official_document_id, external_identifier, "
                "status, retrieved_at) VALUES (:id, :publication_id, :election_id, :document_id, "
                "'synthetic-unmapped-style', 'draft', CURRENT_TIMESTAMP)"
            ),
            {
                "id": unmapped_ballot_id,
                "publication_id": publication_id,
                "election_id": election_id,
                "document_id": document_id,
            },
        )

    with pytest.raises(DatabaseError, match="must have geographic requirements"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE ballot_versions SET status = 'published', published_at = CURRENT_TIMESTAMP "
                    "WHERE id = :id"
                ),
                {"id": unmapped_ballot_id},
            )

    with pytest.raises(DatabaseError, match="published ballot geographic requirements are immutable"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "DELETE FROM ballot_geographic_requirements "
                    "WHERE ballot_version_id = :ballot_id"
                ),
                {"ballot_id": ballot_version_id},
            )

    with pytest.raises(DatabaseError, match="published ballot items are immutable"):
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM ballot_items WHERE ballot_version_id = :ballot_id"),
                {"ballot_id": ballot_version_id},
            )

    with pytest.raises(DatabaseError, match="verified boundary versions are immutable"):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE boundary_versions SET effective_to = DATE '2026-12-31' WHERE id = :id"),
                {"id": boundary_version_id},
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

    with engine.begin() as connection:
        cross_publisher_dataset = connection.execute(
            text(
                "INSERT INTO boundary_datasets "
                "(id, publisher_authority_id, subject_authority_id, authority_source_registry_id, "
                "source_url, checked_at, status) "
                "VALUES (gen_random_uuid(), :publisher_id, :subject_id, :registry_id, "
                "'https://example.test/state-published-county-boundary', CURRENT_TIMESTAMP, 'registered') "
                "RETURNING publisher_authority_id, subject_authority_id"
            ),
            {
                "publisher_id": authority_id,
                "subject_id": second_authority_id,
                "registry_id": registry_entry_id,
            },
        ).mappings().one()

    assert str(cross_publisher_dataset["publisher_authority_id"]) == authority_id
    assert str(cross_publisher_dataset["subject_authority_id"]) == second_authority_id

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

    automatic_alert_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO source_alerts (id, authority_source_registry_id, alert_type) "
                "VALUES (:id, :registry_id, 'verification_overdue')"
            ),
            {"id": automatic_alert_id, "registry_id": registry_entry_id},
        )
        connection.execute(
            text(
                "INSERT INTO source_verification_checks "
                "(id, authority_source_registry_id, checked_at, result, checker_reference, next_check_at, check_method) "
                "VALUES (:id, :registry_id, CURRENT_TIMESTAMP, 'unchanged', 'test-researcher', "
                "CURRENT_TIMESTAMP + INTERVAL '7 days', 'manual')"
            ),
            {"id": str(uuid4()), "registry_id": registry_entry_id},
        )
        automatic_alert = connection.execute(
            text("SELECT status, resolution FROM source_alerts WHERE id = :id"),
            {"id": automatic_alert_id},
        ).mappings().one()

    assert automatic_alert["status"] == "resolved"
    assert automatic_alert["resolution"] == "automatic_unchanged"

    automated_alert_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO source_alerts (id, authority_source_registry_id, alert_type) "
                "VALUES (:id, :registry_id, 'verification_overdue')"
            ),
            {"id": automated_alert_id, "registry_id": registry_entry_id},
        )
        connection.execute(
            text(
                "INSERT INTO source_verification_checks "
                "(id, authority_source_registry_id, checked_at, result, checker_reference, next_check_at, check_method) "
                "VALUES (:id, :registry_id, CURRENT_TIMESTAMP, 'unchanged', 'source-monitor', "
                "CURRENT_TIMESTAMP + INTERVAL '1 day', 'automated')"
            ),
            {"id": str(uuid4()), "registry_id": registry_entry_id},
        )
        automated_alert = connection.execute(
            text("SELECT status FROM source_alerts WHERE id = :id"),
            {"id": automated_alert_id},
        ).scalar_one()

    assert automated_alert == "open"

    changed_check_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO source_verification_checks "
                "(id, authority_source_registry_id, checked_at, result, checker_reference, next_check_at, check_method) "
                "VALUES (:id, :registry_id, CURRENT_TIMESTAMP + INTERVAL '1 hour', 'changed', 'test-researcher', "
                "CURRENT_TIMESTAMP + INTERVAL '7 days', 'manual')"
            ),
            {"id": changed_check_id, "registry_id": registry_entry_id},
        )
        changed_alert = connection.execute(
            text(
                "SELECT alert_type, source_verification_check_id FROM source_alerts "
                "WHERE authority_source_registry_id = :registry_id AND alert_type = 'source_changed' AND status = 'open'"
            ),
            {"registry_id": registry_entry_id},
        ).mappings().one()
        schedule = connection.execute(
            text(
                "SELECT last_checked_at, next_check_at FROM authority_source_registry WHERE id = :registry_id"
            ),
            {"registry_id": registry_entry_id},
        ).mappings().one()

    assert str(changed_alert["source_verification_check_id"]) == changed_check_id
    assert schedule["last_checked_at"] is not None
    assert schedule["next_check_at"] is not None

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
