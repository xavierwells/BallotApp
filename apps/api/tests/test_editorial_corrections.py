from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.editorial_review import prepare_section_submission, unchanged_race_keys
from app.routers.editorial import SectionReviewRequest


@pytest.fixture
def manifest():
    return {
        "schemaVersion": 1, "status": "staged", "organizationSlug": "synthetic", "publicationSlug": "synthetic",
        "county": "Synthetic County",
        "sourceDocument": {"title": "Synthetic certificate", "publisherName": "Test", "sourceUrl": "https://example.test/source.pdf",
            "checksumSha256": "0" * 64, "contentLengthBytes": 100, "publishedAt": "2026-01-01", "retrievedAt": "2026-01-01",
            "retention": "private", "publicAccess": "metadata_only"},
        "election": {"name": "Synthetic election", "authorityName": "Test", "date": "2026-11-03", "type": "general"},
        "races": [{"key": key, "ballotTitle": title, "governmentLevel": "local", "jurisdictionName": "Test", "sourcePage": "1",
            "candidates": [{"ballotLabel": "Example Canddate", "partyLabel": "Independent"},
                           {"ballotLabel": "Second Candidate", "partyLabel": "None listed"}]}
            for key, title in [("office-one", "Office One"), ("office-two", "Office Two")]],
    }


def section(**updates):
    return {"raceKey": "office-one", "decision": "flagged", "note": "", "corrections": [], **updates}


def test_mixed_submission_keeps_original_and_changes_only_selected_field(manifest):
    original = deepcopy(manifest)
    corrected, audit = prepare_section_submission(manifest, [section(corrections=[
        {"field": "ballotLabel", "candidateIndex": 0, "value": "Example Candidate"}]),
        section(raceKey="office-two", decision="accepted")])
    assert manifest == original
    assert corrected["races"][0]["candidates"][0]["ballotLabel"] == "Example Candidate"
    assert corrected["sourceDocument"] == original["sourceDocument"]
    assert corrected["races"][0]["sourcePage"] == "1"
    assert unchanged_race_keys(manifest, corrected) == {"office-two"}
    assert audit["office-one"] == [{"field": "ballotLabel", "candidateIndex": 0,
        "before": "Example Canddate", "after": "Example Candidate"}]


@pytest.mark.parametrize("correction", [
    {"field": "ballotLabel", "candidateIndex": 0, "value": ""},
    {"field": "ballotLabel", "candidateIndex": 0, "value": " "},
    {"field": "ballotLabel", "candidateIndex": 0, "value": "x" * 256},
    {"field": "ballotLabel", "candidateIndex": 0, "value": "Second Candidate"},
    {"field": "partyLabel", "candidateIndex": 0, "value": "Unknown"},
    {"field": "ballotLabel", "candidateIndex": -1, "value": "Name"},
    {"field": "ballotLabel", "candidateIndex": 4, "value": "Name"},
    {"field": "ballotLabel", "candidateIndex": True, "value": "Name"},
    {"field": "ballotTitle", "candidateIndex": 0, "value": "Title"},
    {"field": "sourcePage", "value": "2"},
    {"field": "ballotLabel", "candidateIndex": 0, "value": "Example Canddate"},
])
def test_reject_invalid_or_unchanged_correction(manifest, correction):
    with pytest.raises(ValueError):
        prepare_section_submission(manifest, [section(corrections=[correction])])


def test_reject_accept_and_correct_in_the_same_submission(manifest):
    with pytest.raises(ValueError, match="later submission"):
        prepare_section_submission(manifest, [section(decision="accepted", corrections=[{"field": "ballotTitle", "value": "Fixed"}])])


def test_flags_need_notes_but_corrections_can_explain_the_issue(manifest):
    with pytest.raises(ValueError, match="Explain"):
        prepare_section_submission(manifest, [section()])
    corrected, changes = prepare_section_submission(manifest, [section(note="The official source itself appears wrong.")])
    assert corrected == manifest and not changes


def test_duplicate_sections_and_fields_are_rejected(manifest):
    with pytest.raises(ValueError, match="distinct"):
        prepare_section_submission(manifest, [section(decision="accepted"), section(decision="accepted")])
    with pytest.raises(ValueError, match="once"):
        prepare_section_submission(manifest, [section(corrections=[{"field": "ballotTitle", "value": "Fixed"},
                                                                {"field": "ballotTitle", "value": "Changed again"}])])


def test_context_or_citation_changes_prevent_acceptance_carry_forward(manifest):
    changed = deepcopy(manifest)
    changed["sourceDocument"]["checksumSha256"] = "1" * 64
    assert unchanged_race_keys(manifest, changed) == set()
    changed = deepcopy(manifest)
    changed["election"]["date"] = "2027-01-01"
    assert unchanged_race_keys(manifest, changed) == set()
    changed = deepcopy(manifest)
    changed["races"][0]["sourcePage"] = "2"
    assert unchanged_race_keys(manifest, changed) == {"office-two"}


def test_api_rejects_hidden_fields_and_missing_confirmation():
    with pytest.raises(ValidationError):
        SectionReviewRequest.model_validate({"sections": [section(decision="accepted")]})
    with pytest.raises(ValidationError):
        SectionReviewRequest.model_validate({"confirmed": True, "sections": [section(decision="accepted", reviewerId="someone-else")]})
