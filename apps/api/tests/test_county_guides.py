from contextlib import nullcontext
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app import county_guides
from app.editorial_auth import require_editor
from app.main import app
from app.routers import editorial, guides
from app.schemas.county_guide import GuideContent, PublishGuideRequest, WithdrawGuideRequest


@pytest.fixture
def public_payload():
    preview = {"county": "Example County", "electionName": "Synthetic election", "electionDate": "2026-11-03",
        "raceCount": 1, "candidateCount": 1, "importedBy": "PRIVATE_STAFF",
        "races": [{"id": str(uuid4()), "key": "example", "ballotTitle": "Example Office", "governmentLevel": "local",
            "jurisdictionName": "Example County", "districtLabel": None, "seatsAvailable": 1, "sourcePage": "1", "pdfPageNumber": 2,
            "candidates": [{"id": str(uuid4()), "ballotLabel": "Example Candidate", "partyLabel": "Independent"}],
            "reviewStatusAtImport": "reviewed", "recordedAcceptances": [{"at": "2026-09-11T12:00:00Z", "reviewer": "PRIVATE_STAFF"}]}]}
    source = {"title": "Synthetic official source", "publisher_name": "Example Authority", "source_url": "https://example.test/doc.pdf",
        "checksum_sha256": "a" * 64, "document_published_at": None, "retrieved_at": datetime(2026, 9, 11, tzinfo=UTC),
        "storage_key": "PRIVATE_STORAGE_KEY"}
    return county_guides.public_content(preview, source)


def test_public_projection_excludes_every_private_preview_field(public_payload):
    value = GuideContent.model_validate(public_payload)
    assert value.exactMatch is False and value.completeBallot is False
    assert value.races[0].reviewedAt.day == 11
    serialized = value.model_dump_json()
    for private in ("PRIVATE_STAFF", "PRIVATE_STORAGE_KEY", "importedBy", "recordedAcceptances", "batchId", "reviewer", "note"):
        assert private not in serialized
    with pytest.raises(ValidationError):
        GuideContent.model_validate({**public_payload, "staff": "Never public"})


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///private.pdf", "/api/v1/editorial/private", "https://secret:token@example.test/doc.pdf"])
def test_public_source_is_only_a_direct_safe_publisher_link(public_payload, url):
    public_payload["source"]["url"] = url
    with pytest.raises(ValidationError):
        GuideContent.model_validate(public_payload)


@pytest.mark.parametrize("payload", [
    {"confirmed": False, "basisHash": "a" * 64, "expectedEventId": None},
    {"confirmed": True, "basisHash": "invalid", "expectedEventId": None},
    {"confirmed": True, "basisHash": "a" * 64},
    {"confirmed": True, "basisHash": "a" * 64, "expectedEventId": None, "canPublish": True},
])
def test_publication_requires_confirmation_and_explicit_state_token(payload):
    with pytest.raises(ValidationError):
        PublishGuideRequest.model_validate(payload)


class ReadConnection:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def execute(self, statement, params):
        sql = str(statement)
        assert not any(word in sql.upper().split() for word in ("INSERT", "UPDATE", "DELETE"))
        self.calls.append((sql, params))
        return self

    def mappings(self): return self
    def one_or_none(self): return self.rows[0] if self.rows else None
    def all(self): return self.rows


def test_public_reads_are_scoped_to_latest_explicit_event_not_latest_draft(public_payload, monkeypatch):
    monkeypatch.setenv("BALLOT_BROWSE_ORGANIZATION_SLUG", "example-org")
    monkeypatch.setenv("BALLOT_BROWSE_PUBLICATION_SLUG", "example-pub")
    release = uuid4()
    connection = ReadConnection([{"id": release, "payload": public_payload, "published_at": datetime.now(UTC)}])
    value = county_guides.read_public_guide(connection, release)
    assert value.releaseId == release
    sql, params = connection.calls[0]
    assert params["organization"] == "example-org" and params["publication"] == "example-pub"
    assert "newer.id>e.id" in sql and "e.action='publish'" in sql and "s.approval_status='approved'" in sql
    assert "n.version" not in sql and "newer.version" not in sql  # new drafts do not unpublish


def test_public_pagination_is_bounded_and_does_not_return_whole_rosters(public_payload):
    rows = [{"id": uuid4(), "payload": public_payload, "published_at": datetime.now(UTC)} for _ in range(3)]
    connection = ReadConnection(rows)
    result = county_guides.list_public_guides(connection, offset=2, limit=2)
    assert result["hasMore"] and len(result["items"]) == 2 and result["offset"] == 2
    assert "races" not in result["items"][0].model_dump()
    assert connection.calls[0][1]["limit"] == 3


def test_public_missing_or_withdrawn_is_a_generic_404():
    with pytest.raises(HTTPException) as error:
        county_guides.read_public_guide(ReadConnection([]), uuid4())
    assert error.value.status_code == 404


@pytest.mark.parametrize("county", ["Example County", " example county ", "Bell", "%", "x' OR 1=1 --"])
def test_county_directory_filter_is_exact_bound_and_keeps_public_gates(county):
    connection = ReadConnection([])
    result = county_guides.list_public_guides(connection, offset=0, limit=20, county=county)
    assert result["items"] == []
    sql, params = connection.calls[0]
    assert params["county"] == county
    assert "lower(btrim(r.payload->>'county'))=lower(btrim(:county))" in sql
    assert "o.slug=:organization AND p.slug=:publication" in sql
    assert "s.approval_status='approved'" in sql and "newer.id>e.id" in sql
    assert " LIKE " not in sql.upper() and "ILIKE" not in sql.upper()


def test_county_filter_is_documented_and_validated(monkeypatch):
    client = TestClient(app)
    parameters = app.openapi()["paths"]["/api/v1/guides"]["get"]["parameters"]
    assert any(item["name"] == "county" and not item["required"] for item in parameters)
    for county in ("", "c" * 256):
        assert client.get("/api/v1/guides", params={"county": county}).status_code == 422
    connection = ReadConnection([])
    class Engine:
        def connect(self): return nullcontext(connection)
    monkeypatch.setattr(guides, "get_engine", lambda: Engine())
    response = client.get("/api/v1/guides", params={"county": "Example County"})
    assert response.status_code == 200 and response.json()["items"] == []
    assert response.headers["cache-control"] == "no-store"
    assert connection.calls[0][1]["county"] == "Example County"


def test_publisher_permission_comes_from_database_not_user_claim():
    class Connection:
        def execute(self, sql, params): return self
        def scalar_one_or_none(self): return False
    with pytest.raises(HTTPException) as error:
        county_guides.publisher_allowed(Connection(), {"id": uuid4(), "publication_id": uuid4(), "can_publish": True}, required=True)
    assert error.value.status_code == 403


def test_publish_rejects_stale_state_before_writing(monkeypatch):
    monkeypatch.setattr(county_guides, "lock_publication", lambda *args: None)
    monkeypatch.setattr(county_guides, "batch_row", lambda *args, **kwargs: {"batch_key": "example"})
    monkeypatch.setattr(county_guides, "publisher_allowed", lambda *args, **kwargs: True)
    monkeypatch.setattr(county_guides, "latest_event", lambda *args: {"id": 9})
    with pytest.raises(HTTPException) as error:
        county_guides.publish_guide(None, {"publication_id": uuid4()}, uuid4(), "a" * 64, 8)
    assert error.value.status_code == 409


def test_publish_rejects_changed_evidence_before_writing(monkeypatch, public_payload):
    monkeypatch.setattr(county_guides, "lock_publication", lambda *args: None)
    monkeypatch.setattr(county_guides, "batch_row", lambda *args, **kwargs: {"batch_key": "example"})
    monkeypatch.setattr(county_guides, "publisher_allowed", lambda *args, **kwargs: True)
    monkeypatch.setattr(county_guides, "latest_event", lambda *args: None)
    monkeypatch.setattr(county_guides, "prepare_release", lambda *args: ({}, public_payload, "b" * 64))
    with pytest.raises(HTTPException) as error:
        county_guides.publish_guide(None, {"publication_id": uuid4()}, uuid4(), "a" * 64, None)
    assert error.value.status_code == 409


def test_new_endpoints_document_auth_errors_and_never_cache(monkeypatch, public_payload):
    client = TestClient(app)
    batch = str(uuid4())
    assert client.get(f"/api/v1/editorial/guide-preview/{batch}/publication").status_code == 401
    assert client.get("/api/v1/editorial/guide-releases").status_code == 401
    assert client.post(f"/api/v1/editorial/guide-preview/{batch}/publish", headers={"Origin": "https://untrusted.test"},
        json={"confirmed": True, "basisHash": "a" * 64, "expectedEventId": None}).status_code == 403
    schema = app.openapi()
    for suffix in ("publication", "publish"):
        operation = schema["paths"][f"/api/v1/editorial/guide-preview/{{batch_id}}/{suffix}"]["get" if suffix == "publication" else "post"]
        assert operation["security"]
    assert "409" in schema["paths"]["/api/v1/editorial/guide-releases/{release_id}/withdraw"]["post"]["responses"]
    assert "security" not in schema["paths"]["/api/v1/guides"]["get"]
    assert schema["paths"]["/api/v1/editorial/guide-releases"]["get"]["security"]
    preflight = client.options(f"/api/v1/editorial/guide-preview/{batch}/publish", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert preflight.headers["access-control-allow-credentials"] == "true"
    assert client.get("/api/v1/guides?limit=51").status_code == 422
    assert client.get("/api/v1/guides/not-a-uuid").status_code == 422
    class Engine:
        def connect(self): return nullcontext(ReadConnection([]))
    monkeypatch.setattr(guides, "get_engine", lambda: Engine())
    response = client.get("/api/v1/guides")
    assert response.json()["items"] == [] and response.headers["cache-control"] == "no-store"
    response = client.get(f"/api/v1/guides/{uuid4()}")
    assert response.status_code == 404 and response.headers["cache-control"] == "no-store"
    monkeypatch.setattr(guides, "get_engine", lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_DATABASE_DETAILS")))
    response = client.get("/api/v1/guides")
    assert response.status_code == 503 and "PRIVATE_DATABASE_DETAILS" not in response.text


def test_readiness_endpoint_reports_explicit_blocker_without_mutation(monkeypatch):
    value = {"batchId": str(uuid4()), "canPublish": False, "contentReady": False,
        "blockers": [{"code": "content_not_ready", "message": "Review is incomplete."}], "basisHash": None,
        "currentEventId": None, "currentReleaseId": None, "publishedBatchId": None, "state": "unpublished"}
    class Engine:
        def connect(self): return nullcontext(None)
    monkeypatch.setattr(editorial, "get_engine", lambda: Engine())
    monkeypatch.setattr(editorial, "publication_status", lambda *args: value)
    app.dependency_overrides[require_editor] = lambda: {"id": uuid4(), "publication_id": uuid4()}
    try:
        response = TestClient(app).get(f"/api/v1/editorial/guide-preview/{value['batchId']}/publication")
        assert response.status_code == 200 and response.json() == value
        assert "no-store" in response.headers["cache-control"]
    finally:
        app.dependency_overrides.pop(require_editor, None)
