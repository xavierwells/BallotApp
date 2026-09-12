from copy import deepcopy
from datetime import UTC, datetime

import pytest

from app.shared_editorial_reviews import race_identity, race_content, shared_evidence, review_basis_hash
from app.routers.editorial import ImportReviewRequest
from pydantic import ValidationError


@pytest.fixture
def shared_case():
    race = {"key": "example-office", "ballotTitle": "Example Office", "governmentLevel": "state",
            "jurisdictionName": "Example State", "districtLabel": None, "sourcePage": "2",
            "candidates": [{"ballotLabel": "Example Candidate", "partyLabel": "Independent"},
                           {"ballotLabel": "Another Candidate", "partyLabel": "None listed"}]}
    manifest = {"organizationSlug": "example", "publicationSlug": "example", "county": "Alpha County",
        "election": {"name": "Example general", "date": "2026-11-03", "type": "general", "authorityName": "Alpha elections"},
        "sourceDocument": {"checksumSha256": "0" * 64, "sourceUrl": "https://example.test/cert.pdf", "retrievedAt": "2026-01-01"},
        "races": [race]}
    decision = {"id": 1, "reviewer_id": "human-one", "username": "example-reviewer", "active": True,
                "decision": "accepted", "carried_from_decision_id": None, "reviewed_at": datetime(2026, 1, 1, tzinfo=UTC)}
    batch = {"id": "alpha", "manifest": manifest, "content_hash": "0" * 64, "required_reviewers": 1}
    donor = {"batchId": "beta", "county": "Beta County", "race": {**deepcopy(race), "sourcePage": "200"},
             "content": race_content(race), "decisions": [decision]}
    return batch, race, donor


def test_reuses_content_but_keeps_the_actual_county_and_page_reviewed(shared_case):
    batch, race, donor = shared_case
    evidence, counties, blocked = shared_evidence(batch, race, [], {race_identity(batch["manifest"], race): [donor]})
    assert len(evidence) == 1 and not blocked
    assert counties == ["Beta County"]
    assert evidence[0]["sourcePage"] == "200" and evidence[0]["batchId"] == "beta"
    assert race["sourcePage"] == "2" and donor["decisions"][0]["id"] == 1


def test_same_human_in_several_counties_counts_only_once(shared_case):
    batch, race, donor = shared_case
    other = {**deepcopy(donor), "county": "Gamma County", "batchId": "gamma"}
    pool = {race_identity(batch["manifest"], race): [donor, other]}
    assert len(shared_evidence(batch, race, [], pool)[0]) == 1
    assert shared_evidence(batch, race, donor["decisions"], pool)[0] == []


def test_disabled_reviewers_and_flags_cannot_supply_shared_approval(shared_case):
    batch, race, donor = shared_case
    pool = {race_identity(batch["manifest"], race): [donor]}
    donor["decisions"][0]["active"] = False
    assert shared_evidence(batch, race, [], pool)[0] == []
    donor["decisions"][0]["decision"] = "flagged"
    assert "unresolved flag" in shared_evidence(batch, race, [], pool)[2]


@pytest.mark.parametrize("field,value", [("ballotTitle", "Different Office"), ("seatsAvailable", 2),
                                        ("candidates", [{"ballotLabel": "Different Candidate", "partyLabel": "Independent"}])])
def test_differing_content_pauses_reuse(shared_case, field, value):
    batch, race, donor = shared_case
    donor["race"][field] = value
    donor["content"] = race_content(donor["race"])
    evidence, _, blocked = shared_evidence(batch, race, [], {race_identity(batch["manifest"], race): [donor]})
    assert evidence == [] and "differ" in blocked


@pytest.mark.parametrize("part,field,value", [
    ("manifest", "publicationSlug", "other"), ("manifest", "organizationSlug", "other"),
    ("election", "date", "2028-11-07"), ("election", "type", "primary"),
    ("election", "name", "Other election"), ("sourceDocument", "checksumSha256", "1" * 64),
    ("race", "jurisdictionName", "Another State"), ("race", "districtLabel", "District 2"),
    ("race", "governmentLevel", "federal"), ("race", "key", "other-office"),
])
def test_distinct_race_source_election_or_tenant_never_matches(shared_case, part, field, value):
    batch, race, _ = shared_case
    manifest = deepcopy(batch["manifest"])
    target = manifest if part == "manifest" else manifest["races"][0] if part == "race" else manifest[part]
    target[field] = value
    assert race_identity(manifest, manifest["races"][0]) != race_identity(batch["manifest"], race)


def test_county_administrator_page_and_candidate_order_are_not_shared_content(shared_case):
    batch, race, _ = shared_case
    manifest = deepcopy(batch["manifest"])
    manifest["county"] = "Beta County"
    manifest["election"]["authorityName"] = "Beta elections"
    manifest["sourceDocument"]["retrievedAt"] = "2026-02-01"
    manifest["races"][0]["sourcePage"] = "200"
    manifest["races"][0]["candidates"].reverse()
    assert race_identity(manifest, manifest["races"][0]) == race_identity(batch["manifest"], race)
    assert race_content(manifest["races"][0]) == race_content(race)


@pytest.mark.parametrize("level", ["county", "local", "municipal", "unknown"])
def test_unscoped_local_office_names_do_not_link_counties(shared_case, level):
    batch, race, _ = shared_case
    race["governmentLevel"] = level
    other = deepcopy(batch["manifest"])
    other["county"] = "Beta County"
    assert race_identity(other, other["races"][0]) != race_identity(batch["manifest"], race)


def test_import_basis_changes_when_evidence_or_threshold_changes(shared_case):
    batch, _, _ = shared_case
    before = review_basis_hash(batch, [{"decisions": [{"decisionId": "1"}]}])
    assert review_basis_hash(batch, [{"decisions": [{"decisionId": "2"}]}]) != before
    batch["required_reviewers"] = 2
    assert review_basis_hash(batch, [{"decisions": [{"decisionId": "1"}]}]) != before


def test_import_confirmation_cannot_supply_a_reviewer_name():
    with pytest.raises(ValidationError):
        ImportReviewRequest.model_validate({"confirmedCountyCoverage": True, "username": "someone-else"})
    with pytest.raises(ValidationError):
        ImportReviewRequest.model_validate({"confirmedCountyCoverage": "true"})
    with pytest.raises(ValidationError):
        ImportReviewRequest.model_validate({"reviewBasisHash": "not-a-hash"})
