"""Run against isolated PostgreSQL; never point TEST_DATABASE_URL at pilot data."""

from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from app.cli.bootstrap_authorities import bootstrap
from app.cli.intake_document import intake_document
from app.cli.review_source import review_source
from app.database import get_engine
from app.editorial_auth import create_user
from app.editorial_review import stage_batch
from app.main import app

pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Isolated TEST_DATABASE_URL required")
ORIGIN = {"Origin": "http://localhost:3000"}
PASSPHRASE = "synthetic test passphrase only"


@pytest.fixture
def dataset(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", "http://localhost:3000")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "private"))
    get_engine.cache_clear()
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
    suffix = uuid4().hex[:10]
    org = f"review-org-{suffix}"
    bootstrap({"publication": {"organizationSlug": org, "organizationName": "Test", "slug": "test", "name": "Test"},
               "authorities": [{"slug": "test", "name": "Test County", "authorityType": "county",
                   "officialWebsiteUrl": "https://example.test", "sources": [{"slug": "cert", "name": "Certificate",
                   "sourceUrl": "https://example.test/cert.pdf", "sourceCategory": "candidate_filings"}]}]})
    engine = get_engine()
    review_source(engine=engine, organization_slug=org, publication_slug="test", authority_slug="test", source_slug="cert",
        approval_status="approved", permitted_use="private_retention", reviewer_reference="test-policy", reviewed_at=datetime.now(UTC),
        review_notes="Synthetic fixture", terms_url="https://example.test/terms", source_license="Synthetic", cost_model="free",
        rate_limit="manual", retention_rule="private", attribution_requirement="Test", redistribution_rights="metadata_only",
        next_review_at=None, automated_monitoring_allowed=False)
    pdf = tmp_path / "source.pdf"
    content = b"%PDF-1.4\nSynthetic source only\n%%EOF"
    pdf.write_bytes(content)
    document_id = intake_document(organization_slug=org, publication_slug="test", authority_slug="test", source_slug="cert",
        file_path=pdf, title="Synthetic source", publisher_name="Test", source_url="https://example.test/cert.pdf",
        retrieved_at=datetime.now(UTC), document_published_at=None, public_access_level="metadata_only")
    manifest = {"schemaVersion": 1, "status": "staged", "organizationSlug": org, "publicationSlug": "test",
        "county": "Test County", "election": {"name": "Test election", "authorityName": "Test County", "date": "2026-11-03", "type": "general"},
        "sourceDocument": {"title": "Synthetic source", "publisherName": "Test", "sourceUrl": "https://example.test/cert.pdf",
            "checksumSha256": hashlib.sha256(content).hexdigest(), "contentLengthBytes": len(content), "publishedAt": "2026-01-01",
            "retrievedAt": "2026-09-11", "retention": "private", "publicAccess": "metadata_only"},
        "races": [{"key": "test-office", "ballotTitle": "Example Office", "governmentLevel": "local",
                   "jurisdictionName": "Test County", "districtLabel": None, "sourcePage": "1",
                   "candidates": [{"ballotLabel": "Example Candidate", "partyLabel": "Independent"}]}]}
    username = f"reviewer-{suffix}"
    with engine.begin() as connection:
        publication_id = connection.execute(text(
            "SELECT p.id FROM publications p JOIN organizations o ON o.id=p.organization_id WHERE o.slug=:o"
        ), {"o": org}).scalar_one()
        create_user(connection, publication_id, username, PASSPHRASE)
        batch_id = stage_batch(connection, publication_id, document_id, manifest)
    yield {"engine": engine, "publication": publication_id, "document": document_id,
           "batch": batch_id, "manifest": manifest, "username": username, "content": content}
    get_engine.cache_clear()


def signed_in(dataset):
    client = TestClient(app)
    response = client.post("/api/v1/editorial/login", headers=ORIGIN,
                           json={"username": dataset["username"], "password": PASSPHRASE})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    return client


def test_private_drafts_review_flag_resume_import_and_logout(dataset):
    client = signed_in(dataset)
    base = f"/api/v1/editorial/batches/{dataset['batch']}"
    assert client.get(base).json()["races"][0]["reviewStatus"] == "unreviewed"
    assert client.post(base + "/import", headers=ORIGIN).status_code == 409
    assert client.post(base + "/decisions", headers={"Origin": "https://other.example"},
                       json={"raceKeys": ["test-office"], "decision": "accepted"}).status_code == 403
    assert client.post(base + "/decisions", headers=ORIGIN,
                       json={"raceKeys": ["unknown"], "decision": "accepted"}).status_code == 422
    assert client.get(base + "/source").content == dataset["content"]
    response = client.post(base + "/decisions", headers=ORIGIN,
        json={"raceKeys": ["test-office"], "decision": "flagged", "note": "Check spelling"})
    assert response.json()["races"][0]["reviewStatus"] == "flagged"
    assert client.post(base + "/import", headers=ORIGIN).status_code == 409
    client = signed_in(dataset)
    assert client.get(base).json()["races"][0]["decisions"][0]["note"] == "Check spelling"
    response = client.post(base + "/decisions", headers=ORIGIN,
        json={"raceKeys": ["test-office"], "decision": "accepted", "note": "Checked the source"})
    assert response.json()["reviewedRaces"] == 1
    assert client.post(base + "/import", headers=ORIGIN).json()["imported"] is True
    assert client.post(base + "/import", headers=ORIGIN).json()["imported"] is True
    with dataset["engine"].connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM candidates WHERE publication_id=:p"), {"p": dataset["publication"]}).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM ballot_versions WHERE publication_id=:p"), {"p": dataset["publication"]}).scalar_one() == 0
    # A corrected spelling must not silently create a second canonical candidacy.
    with dataset["engine"].begin() as connection:
        changed = deepcopy(dataset["manifest"])
        changed["races"][0]["candidates"][0]["ballotLabel"] = "Corrected Example Candidate"
        revised_id = stage_batch(connection, dataset["publication"], dataset["document"], changed)
    revised = f"/api/v1/editorial/batches/{revised_id}"
    assert client.post(revised + "/decisions", headers=ORIGIN,
        json={"raceKeys": ["test-office"], "decision": "accepted"}).status_code == 200
    assert client.post(revised + "/import", headers=ORIGIN).status_code == 409
    with dataset["engine"].connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM candidates WHERE publication_id=:p"), {"p": dataset["publication"]}).scalar_one() == 1
    assert client.post("/api/v1/editorial/logout", headers=ORIGIN).status_code == 200
    assert client.get(base + "/source").status_code == 401


def test_new_revision_loses_approval_and_other_publication_is_hidden(dataset):
    client = signed_in(dataset)
    old = f"/api/v1/editorial/batches/{dataset['batch']}"
    client.post(old + "/decisions", headers=ORIGIN, json={"raceKeys": ["test-office"], "decision": "accepted"})
    with dataset["engine"].begin() as connection:
        assert stage_batch(connection, dataset["publication"], dataset["document"], dataset["manifest"]) == dataset["batch"]
        revised = deepcopy(dataset["manifest"])
        revised["races"][0]["candidates"][0]["ballotLabel"] = "Corrected Example"
        new_id = stage_batch(connection, dataset["publication"], dataset["document"], revised)
    assert client.get(f"/api/v1/editorial/batches/{new_id}").json()["reviewedRaces"] == 0
    assert client.post(old + "/import", headers=ORIGIN).status_code == 409
    assert client.post(old + "/decisions", headers=ORIGIN, json={"raceKeys": ["test-office"], "decision": "accepted"}).status_code == 409
    with dataset["engine"].begin() as connection:
        organization = connection.execute(text("SELECT organization_id FROM publications WHERE id=:id"), {"id": dataset["publication"]}).scalar_one()
        other = connection.execute(text("INSERT INTO publications(id,organization_id,slug,name) VALUES(gen_random_uuid(),:o,:s,'Other') RETURNING id"),
                                   {"o": organization, "s": f"other-{uuid4().hex[:8]}"}).scalar_one()
        other_name = f"other-{uuid4().hex[:8]}"
        create_user(connection, other, other_name, PASSPHRASE)
    outsider = signed_in({**dataset, "username": other_name})
    assert outsider.get(old).status_code == 404
    assert outsider.get(old + "/source").status_code == 404
    assert outsider.post(old + "/decisions", headers=ORIGIN, json={"raceKeys": ["test-office"], "decision": "accepted"}).status_code == 404
    assert outsider.post(old + "/review", headers=ORIGIN, json={"confirmed": True,
        "sections": [{"raceKey": "test-office", "decision": "accepted"}]}).status_code == 404
    with pytest.raises(DatabaseError):
        with dataset["engine"].begin() as connection:
            connection.execute(text("DELETE FROM editorial_decisions WHERE batch_id=:b"), {"b": dataset["batch"]})


def test_failed_login_lockout_and_session_revocation(dataset):
    client = TestClient(app)
    for _ in range(5):
        assert client.post("/api/v1/editorial/login", headers=ORIGIN,
            json={"username": dataset["username"], "password": "wrong"}).status_code == 401
    assert client.post("/api/v1/editorial/login", headers=ORIGIN,
        json={"username": dataset["username"], "password": PASSPHRASE}).status_code == 401
    with dataset["engine"].begin() as connection:
        connection.execute(text("UPDATE editorial_users SET locked_until=NULL WHERE username=:u"), {"u": dataset["username"]})
    first = signed_in(dataset)
    second = signed_in(dataset)
    assert first.get("/api/v1/editorial/me").status_code == 401
    assert second.get("/api/v1/editorial/me").status_code == 200


def test_section_corrections_preserve_other_reviews_and_survive_setup(dataset):
    manifest = deepcopy(dataset["manifest"])
    for key in ("second-office", "third-office"):
        manifest["races"].append({**deepcopy(manifest["races"][0]), "key": key, "ballotTitle": key})
    with dataset["engine"].begin() as connection:
        original_id = stage_batch(connection, dataset["publication"], dataset["document"], manifest)
    client = signed_in(dataset)
    original = f"/api/v1/editorial/batches/{original_id}"
    assert client.post(original + "/decisions", headers=ORIGIN,
        json={"raceKeys": ["test-office", "second-office"], "decision": "accepted"}).status_code == 200
    original_review_time = client.get(original).json()["races"][1]["decisions"][0]["at"]
    with dataset["engine"].begin() as connection:
        second_name = f"second-{uuid4().hex[:8]}"
        create_user(connection, dataset["publication"], second_name, PASSPHRASE)
    second_reviewer = signed_in({**dataset, "username": second_name})
    assert second_reviewer.post(original + "/decisions", headers=ORIGIN, json={
        "raceKeys": ["test-office"], "decision": "flagged", "note": "Name needs correction",
    }).status_code == 200
    response = client.post(original + "/review", headers=ORIGIN, json={"confirmed": True, "sections": [
        {"raceKey": "test-office", "decision": "flagged", "corrections": [
            {"field": "ballotLabel", "candidateIndex": 0, "value": "Corrected Candidate"}]},
        {"raceKey": "third-office", "decision": "flagged", "note": "Source itself needs clarification"},
    ]})
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["id"] != original_id
    rows = {row["key"]: row for row in updated["races"]}
    assert rows["test-office"]["reviewStatus"] == "flagged"
    assert rows["test-office"]["approvalCount"] == 0
    assert rows["test-office"]["candidates"][0]["ballotLabel"] == "Corrected Candidate"
    assert rows["test-office"]["corrections"][0]["changes"][0]["before"] == "Example Candidate"
    assert rows["second-office"]["reviewStatus"] == "reviewed"
    assert rows["second-office"]["decisions"][0]["carriedForward"] is True
    assert rows["second-office"]["decisions"][0]["at"] == original_review_time
    carried_flag = next(d for d in rows["test-office"]["decisions"] if d["reviewer"] == second_name)
    assert carried_flag["decision"] == "flagged" and carried_flag["carriedForward"] is True
    assert rows["third-office"]["decisions"][0]["note"] == "Source itself needs clarification"
    assert client.get(original).json()["races"][0]["candidates"][0]["ballotLabel"] == "Example Candidate"
    revised = f"/api/v1/editorial/batches/{updated['id']}"
    assert client.post(revised + "/import", headers=ORIGIN).status_code == 409
    assert client.post(original + "/review", headers=ORIGIN,
        json={"confirmed": True, "sections": [{"raceKey": "test-office", "decision": "accepted"}]}).status_code == 409
    with dataset["engine"].begin() as connection:
        assert stage_batch(connection, dataset["publication"], dataset["document"], manifest) == updated["id"]
    response = client.post(revised + "/review", headers=ORIGIN, json={"confirmed": True, "sections": [
        {"raceKey": "test-office", "decision": "accepted"}, {"raceKey": "third-office", "decision": "accepted"},
    ]})
    assert response.status_code == 200 and response.json()["reviewedRaces"] == 2
    # Correcting text and accepting it cannot resolve another reviewer's flag.
    assert client.post(revised + "/import", headers=ORIGIN).status_code == 409
    response = second_reviewer.post(revised + "/review", headers=ORIGIN, json={"confirmed": True,
        "sections": [{"raceKey": "test-office", "decision": "accepted"}]})
    assert response.status_code == 200 and response.json()["reviewedRaces"] == 3
    assert client.post(revised + "/import", headers=ORIGIN).json()["imported"] is True
    assert client.post(revised + "/review", headers=ORIGIN, json={"confirmed": True,
        "sections": [{"raceKey": "test-office", "decision": "flagged", "note": "Already imported"}]}).status_code == 409
    with dataset["engine"].connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM candidates WHERE publication_id=:p AND canonical_name='Corrected Candidate'"),
                                  {"p": dataset["publication"]}).scalar_one() == 1
    with pytest.raises(DatabaseError, match="immutable"):
        with dataset["engine"].begin() as connection:
            connection.execute(text("DELETE FROM editorial_corrections WHERE batch_id=:b"), {"b": updated["id"]})


def test_invalid_multi_section_submission_does_not_write_partial_review(dataset):
    client = signed_in(dataset)
    base = f"/api/v1/editorial/batches/{dataset['batch']}"
    response = client.post(base + "/review", headers=ORIGIN, json={"confirmed": True, "sections": [
        {"raceKey": "test-office", "decision": "accepted"},
        {"raceKey": "does-not-exist", "decision": "flagged", "note": "Invalid section"},
    ]})
    assert response.status_code == 422
    assert client.get(base).json()["reviewedRaces"] == 0
    with dataset["engine"].connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM editorial_decisions WHERE batch_id=:b"), {"b": dataset["batch"]}).scalar_one() == 0
    assert client.post(base + "/review", headers={"Origin": "https://untrusted.example"},
        json={"confirmed": True, "sections": [{"raceKey": "test-office", "decision": "accepted"}]}).status_code == 403


def test_restoring_old_text_never_restores_its_old_acceptance(dataset):
    client = signed_in(dataset)
    base = f"/api/v1/editorial/batches/{dataset['batch']}"
    client.post(base + "/decisions", headers=ORIGIN, json={"raceKeys": ["test-office"], "decision": "accepted"})
    for title in ("Corrected Office", "Example Office"):
        result = client.post(base + "/review", headers=ORIGIN, json={"confirmed": True, "sections": [
            {"raceKey": "test-office", "decision": "flagged", "corrections": [{"field": "ballotTitle", "value": title}]},
        ]})
        assert result.status_code == 200, result.text
        assert result.json()["races"][0]["approvalCount"] == 0
        base = f"/api/v1/editorial/batches/{result.json()['id']}"
    assert client.post(base + "/import", headers=ORIGIN).status_code == 409


def shared_counties(dataset, *, required=1):
    """Synthetic state race repeated in county sections of the same document."""
    manifests, ids = [], []
    with dataset["engine"].begin() as connection:
        for county, page in [("Alpha County", "2"), ("Beta County", "20"), ("Gamma County", "200")]:
            manifest = deepcopy(dataset["manifest"])
            manifest["county"] = county
            manifest["election"]["authorityName"] = county
            manifest["races"][0].update(governmentLevel="state", jurisdictionName="Synthetic State", sourcePage=page)
            if required == 1:
                batch_id = stage_batch(connection, dataset["publication"], dataset["document"], manifest)
            else:
                from app.editorial_review import content_hash
                import json
                batch_id = str(connection.execute(text(
                    "INSERT INTO editorial_batches(id,publication_id,batch_key,document_id,content_hash,manifest,required_reviewers) "
                    "VALUES(gen_random_uuid(),:p,:k,:d,:h,CAST(:m AS jsonb),:required) RETURNING id"
                ), {"p": dataset["publication"], "k": f"2026-11-03:general:{county}", "d": dataset["document"],
                    "h": content_hash(manifest), "m": json.dumps(manifest), "required": required}).scalar_one())
            ids.append(batch_id)
            manifests.append(manifest)
    return [f"/api/v1/editorial/batches/{id}" for id in ids], manifests


def accept_section(client, base):
    return client.post(base + "/review", headers=ORIGIN, json={"confirmed": True,
        "sections": [{"raceKey": "test-office", "decision": "accepted"}]})


def test_shared_reviews_need_county_confirmation_and_preserve_import_evidence(dataset):
    (alpha, beta, _), manifests = shared_counties(dataset)
    client = signed_in(dataset)
    assert accept_section(client, alpha).status_code == 200
    shared = client.get(beta).json()
    assert shared["reviewedRaces"] == shared["sharedReviewedRaces"] == 1
    assert shared["requiresCountyConfirmation"] is True
    assert shared["races"][0]["decisions"] == []  # No invented beta-page check.
    evidence = shared["races"][0]["sharedReviews"][0]
    assert evidence["county"] == "Alpha County" and evidence["sourcePage"] == "2"
    assert shared["races"][0]["sourcePage"] == "20"
    assert evidence["reviewer"] == dataset["username"]
    assert client.post(beta + "/import", headers=ORIGIN).status_code == 409
    assert client.post(beta + "/import", headers=ORIGIN,
        json={"confirmedCountyCoverage": True, "reviewBasisHash": "0" * 64}).status_code == 409
    # The command-line canonical importer cannot skip the county confirmation.
    from app.cli.stage_candidate_certification import apply_manifest
    with pytest.raises(ValueError, match="county"):
        with dataset["engine"].begin() as connection:
            apply_manifest(manifests[1], connection=connection)
    result = client.post(beta + "/import", headers=ORIGIN,
        json={"confirmedCountyCoverage": True, "reviewBasisHash": shared["reviewBasisHash"]})
    assert result.status_code == 200, result.text
    assert result.json()["imported"] and result.json()["countySourceConfirmedBy"] == dataset["username"]
    with dataset["engine"].connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM editorial_decisions WHERE batch_id=:id"),
                                  {"id": shared["id"]}).scalar_one() == 0
        receipt = connection.execute(text("SELECT review_snapshot FROM editorial_promotions WHERE batch_id=:id"),
                                     {"id": shared["id"]}).scalar_one()
        assert receipt["races"][0]["sharedReviews"][0]["decisionId"] == evidence["decisionId"]
    # An import receipt stays historical even when later live evidence changes.
    assert client.post(alpha + "/decisions", headers=ORIGIN, json={"raceKeys": ["test-office"],
        "decision": "flagged", "note": "Later question about this transcription"}).status_code == 200
    historical = client.get(beta).json()
    assert historical["races"] == result.json()["races"]
    assert client.post(beta + "/import", headers=ORIGIN).json()["imported"] is True
    with pytest.raises(DatabaseError, match="immutable"):
        with dataset["engine"].begin() as connection:
            connection.execute(text("UPDATE editorial_promotions SET review_snapshot=NULL WHERE batch_id=:id"),
                               {"id": shared["id"]})


def test_shared_review_changes_flags_and_current_revisions_fail_closed(dataset):
    (alpha, beta, gamma), _ = shared_counties(dataset)
    client = signed_in(dataset)
    assert accept_section(client, alpha).status_code == 200
    earlier_basis = client.get(beta).json()["reviewBasisHash"]
    assert client.post(gamma + "/decisions", headers=ORIGIN, json={"raceKeys": ["test-office"],
        "decision": "flagged", "note": "Check this county's source"}).status_code == 200
    paused = client.get(beta).json()
    assert paused["reviewedRaces"] == 0 and paused["races"][0]["sharedReviewBlockedReason"]
    assert client.post(beta + "/import", headers=ORIGIN,
        json={"confirmedCountyCoverage": True, "reviewBasisHash": earlier_basis}).status_code == 409
    assert accept_section(client, gamma).status_code == 200
    assert client.get(beta).json()["races"][0]["approvalCount"] == 1  # Same human, two counties.
    corrected = client.post(alpha + "/review", headers=ORIGIN, json={"confirmed": True, "sections": [{
        "raceKey": "test-office", "decision": "flagged", "corrections": [
            {"field": "ballotLabel", "candidateIndex": 0, "value": "Corrected Candidate"}]}]}).json()
    current_alpha = f"/api/v1/editorial/batches/{corrected['id']}"
    assert accept_section(client, current_alpha).status_code == 200
    paused = client.get(beta).json()
    assert paused["reviewedRaces"] == 0 and "differ" in paused["races"][0]["sharedReviewBlockedReason"]
    assert paused["races"][0]["candidates"][0]["ballotLabel"] == "Example Candidate"  # No automatic peer edit.
    # No review may be borrowed from alpha's now-superseded old text.
    with dataset["engine"].begin() as connection:
        connection.execute(text("UPDATE editorial_users SET active=FALSE WHERE username=:u"), {"u": dataset["username"]})
    assert client.get(beta).status_code == 401


def test_shared_reviews_count_distinct_active_humans_not_counties(dataset):
    (alpha, beta, gamma), _ = shared_counties(dataset, required=2)
    first = signed_in(dataset)
    assert accept_section(first, alpha).status_code == 200
    assert accept_section(first, gamma).status_code == 200
    assert first.get(beta).json()["reviewedRaces"] == 0
    assert first.get(beta).json()["races"][0]["approvalCount"] == 1
    with dataset["engine"].begin() as connection:
        name = f"second-{uuid4().hex[:8]}"
        create_user(connection, dataset["publication"], name, PASSPHRASE)
    second = signed_in({**dataset, "username": name})
    assert accept_section(second, alpha).status_code == 200
    assert second.get(beta).json()["reviewedRaces"] == 1
    with dataset["engine"].begin() as connection:
        connection.execute(text("UPDATE editorial_users SET active=FALSE WHERE username=:u"), {"u": dataset["username"]})
    result = second.get(beta).json()
    assert result["reviewedRaces"] == 0 and result["races"][0]["approvalCount"] == 1


@pytest.mark.parametrize(("claim_type", "required"), [("verified_fact", 1), ("editorial_analysis", 2), ("candidate_statement", 2)])
def test_content_policy_counts_authenticated_reviewers_and_rejects_stale_review(dataset, claim_type, required):
    engine = dataset["engine"]
    claim_id = uuid4()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO source_claims(id,publication_id,document_id,claim_type,subject_type,subject_id,claim_text) "
                                "VALUES(:id,:p,:d,:t,'candidate',:subject,'Synthetic statement')"),
                           {"id": claim_id, "p": dataset["publication"], "d": dataset["document"], "t": claim_type, "subject": uuid4()})
        staff_id = connection.execute(text("SELECT id FROM editorial_users WHERE username=:u"), {"u": dataset["username"]}).scalar_one()
    def approval(user_id, username):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO verification_events(id,publication_id,source_claim_id,action,target_type,target_id,actor_reference,actor_role,editorial_user_id,review_fingerprint) "
                                    "VALUES(gen_random_uuid(),:p,:c,'verified','source_claim',:c,:u,'verifier',:staff,editorial_target_fingerprint('source_claim',:c))"),
                               {"p": dataset["publication"], "c": claim_id, "u": username, "staff": user_id})
    def publish():
        with engine.begin() as connection:
            connection.execute(text("UPDATE source_claims SET editorial_status='published',published_at=CURRENT_TIMESTAMP,last_verified_at=CURRENT_TIMESTAMP WHERE id=:id"), {"id": claim_id})
    approval(staff_id, dataset["username"])
    if required == 2:
        approval(staff_id, dataset["username"])
        with pytest.raises(DatabaseError, match="requires 2"):
            publish()
        with engine.begin() as connection:
            second_name = f"second-{uuid4().hex[:8]}"
            create_user(connection, dataset["publication"], second_name, PASSPHRASE)
            second_id = connection.execute(text("SELECT id FROM editorial_users WHERE username=:u"), {"u": second_name}).scalar_one()
        approval(second_id, second_name)
    with engine.begin() as connection:
        connection.execute(text("UPDATE source_claims SET claim_text='Changed synthetic statement' WHERE id=:id"), {"id": claim_id})
    with pytest.raises(DatabaseError, match="current content"):
        publish()
    approval(staff_id, dataset["username"])
    if required == 2:
        approval(second_id, second_name)
    publish()
