from contextlib import nullcontext
from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.editorial_auth import require_editor
from app.editorial_preview import assemble_preview, guide_preview, list_previews
from app.main import app
from app.routers import editorial
from app.schemas.editorial_preview import GuidePreview


@pytest.fixture
def imported():
    race = {"key": "example-office", "ballotTitle": "Example Office", "governmentLevel": "state",
            "jurisdictionName": "Example State", "districtLabel": None, "sourcePage": "3",
            "candidates": [{"ballotLabel": "Example Candidate", "partyLabel": "Independent"}]}
    manifest = {"county": "Example County", "election": {"name": "Example election", "date": "2026-11-03",
                "authorityName": "Example authority", "type": "general"}, "races": [race]}
    batch = {"id": uuid4(), "document_id": uuid4(), "version": 2, "manifest": manifest,
             "imported_at": datetime(2026, 9, 12, tzinfo=UTC), "imported_by": "example-reviewer",
             "is_current": True, "source_title": "Synthetic certification", "source_url": "https://example.test/source.pdf",
             "checksum_sha256": "a" * 64,
             "review_snapshot": {"countySourceConfirmedBy": None, "races": [{**deepcopy(race), "reviewStatus": "reviewed",
                "decisions": [{"decision": "accepted", "reviewer": "example-reviewer", "at": "2026-09-11T12:00:00Z",
                               "originalDecisionId": "12", "note": "Private note not for preview"}], "sharedReviews": []}]}}
    rows = [{"race_id": uuid4(), "race_key": race["key"], "ballot_title": race["ballotTitle"], "office_name": race["ballotTitle"],
             "government_level": race["governmentLevel"], "jurisdiction_name": race["jurisdictionName"],
             "district_label": None, "seats_available": 1, "candidate_id": uuid4(),
             "ballot_label": "Example Candidate", "party_label": "Independent", "source_page": "3"}]
    return batch, rows


def test_preview_uses_canonical_ids_and_retains_historical_receipt(imported):
    batch, rows = imported
    preview = GuidePreview.model_validate(assemble_preview(batch, rows))
    assert preview.scope == "private_certification_preview"
    assert preview.exactMatch is False and preview.publicationAllowed is False
    assert preview.races[0].id == rows[0]["race_id"]
    assert preview.races[0].candidates[0].id == rows[0]["candidate_id"]
    assert preview.races[0].recordedAcceptances[0].at.day == 11
    assert preview.importedAt.day == 12
    assert preview.races[0].pdfPageNumber == 3
    assert "Private note" not in preview.model_dump_json()
    assert "storage_key" not in preview.model_dump_json()


@pytest.mark.parametrize("field,value", [
    ("ballot_label", "Changed Candidate"), ("party_label", "Republican"),
    ("ballot_title", "Changed Office"), ("government_level", "local"),
    ("district_label", "District 2"), ("jurisdiction_name", "Other State"),
    ("seats_available", 2), ("source_page", None), ("source_page", "4"), ("candidate_id", None),
])
def test_canonical_or_citation_drift_never_falls_back_to_the_draft(imported, field, value):
    batch, rows = imported
    rows[0][field] = value
    with pytest.raises(HTTPException) as error:
        assemble_preview(batch, rows)
    assert error.value.status_code == 409


def test_incomplete_or_extra_roster_fails_closed(imported):
    batch, rows = imported
    with pytest.raises(HTTPException):
        assemble_preview(batch, [])
    with pytest.raises(HTTPException):
        assemble_preview(batch, rows + [{**rows[0], "candidate_id": uuid4(), "ballot_label": "Extra Candidate"}])
    with pytest.raises(HTTPException):
        assemble_preview(batch, [{**rows[0], "office_name": "Different canonical office"}])


def test_additional_source_pages_do_not_duplicate_candidates(imported):
    batch, rows = imported
    result = assemble_preview(batch, rows + [{**rows[0], "source_page": "4"}])
    assert len(result["races"][0]["candidates"]) == 1


def test_missing_receipt_does_not_invent_a_reviewer(imported):
    batch, rows = imported
    batch["review_snapshot"] = None
    batch["is_current"] = False
    result = GuidePreview.model_validate(assemble_preview(batch, rows))
    assert result.current is False and result.reviewReceiptAvailable is False
    assert result.races[0].reviewStatusAtImport == "unavailable"
    assert result.races[0].recordedAcceptances == []


def test_shared_evidence_remains_separate_from_county_confirmation(imported):
    batch, rows = imported
    receipt = batch["review_snapshot"]
    receipt["countySourceConfirmedBy"] = "county-checker"
    receipt["races"][0]["decisions"] = []
    receipt["races"][0]["sharedReviews"] = [{"reviewer": "donor-reviewer", "at": "2026-09-10T12:00:00Z",
        "originalDecisionId": "8", "county": "Other County", "batchId": str(uuid4()), "sourcePage": "1"}]
    result = GuidePreview.model_validate(assemble_preview(batch, rows))
    assert result.countySourceConfirmedBy == "county-checker"
    assert result.races[0].recordedAcceptances[0].kind == "shared"
    assert result.races[0].recordedAcceptances[0].reviewer == "donor-reviewer"
    receipt["races"][0]["ballotTitle"] = "Different receipt"
    with pytest.raises(HTTPException):
        assemble_preview(batch, rows)


class ReadConnection:
    def __init__(self, batch, rows):
        self.batch, self.rows, self.calls = batch, rows, []

    def execute(self, statement, parameters):
        self.calls.append((str(statement), parameters))
        assert not any(word in str(statement).upper().split() for word in ("INSERT", "UPDATE", "DELETE"))
        return self

    def mappings(self):
        return self

    def one_or_none(self):
        return self.batch

    def all(self):
        return self.rows


def test_preview_queries_are_publication_scoped_and_read_only(imported):
    batch, rows = imported
    publication = uuid4()
    connection = ReadConnection(batch, rows)
    guide_preview(connection, publication, batch["id"])
    assert len(connection.calls) == 2
    assert all(parameters["publication"] == publication for _, parameters in connection.calls)
    assert "editorial_promotions" in connection.calls[0][0]
    assert "e.publication_id=:publication" in connection.calls[1][0]
    assert connection.calls[1][1]["document"] == batch["document_id"]
    assert connection.calls[1][1]["keys"] == ["example-office"]


def test_preview_list_excludes_superseded_imports(imported):
    batch, _ = imported
    connection = ReadConnection(None, [batch])
    assert list_previews(connection, uuid4())[0]["county"] == "Example County"
    statement = connection.calls[0][0]
    assert "AND NOT EXISTS" in statement and "n.version>b.version" in statement
    assert "LIMIT 100" in statement


def test_no_import_receipt_is_indistinguishable_from_inaccessible_batch():
    with pytest.raises(HTTPException) as error:
        guide_preview(ReadConnection(None, []), uuid4(), uuid4())
    assert error.value.status_code == 404


def test_authenticated_endpoint_serializes_private_preview(imported, monkeypatch):
    batch, rows = imported
    class Engine:
        def connect(self):
            return nullcontext(ReadConnection(batch, rows))
    monkeypatch.setattr(editorial, "get_engine", lambda: Engine())
    app.dependency_overrides[require_editor] = lambda: {"publication_id": uuid4(), "username": "synthetic"}
    try:
        response = TestClient(app).get(f"/api/v1/editorial/guide-preview/{batch['id']}")
        assert response.status_code == 200, response.text
        assert response.json()["publicationAllowed"] is False
        assert response.json()["candidateCount"] == 1
        assert "no-store" in response.headers["cache-control"]
    finally:
        app.dependency_overrides.pop(require_editor, None)
