"""Explicit release of reviewed facts; never a ballot-style publication bypass.

Release admission is checked here under the existing publication lock. The DB
also enforces scoped import/actor references, publisher eligibility and immutable
release/event rows. Public readers use only allowlisted frozen release payloads.
"""

import json
import os
import hashlib
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text

from app.editorial_preview import guide_preview
from app.document_storage import DocumentStorageError, document_store_from_environment
from app.editorial_review import batch_row, content_hash, lock_publication, require_reviewed_manifest
from app.schemas.county_guide import GuideContent, PublicGuide, GuideSummary


def publisher_allowed(connection, user, *, required=False):
    # Recheck the database; never trust a client field or an earlier /me result.
    allowed = connection.execute(text(
        "SELECT active AND can_publish FROM editorial_users WHERE id=:u AND publication_id=:p FOR SHARE"
    ), {"u": user["id"], "p": user["publication_id"]}).scalar_one_or_none() is True
    if required and not allowed:
        raise HTTPException(403, "This account does not have publishing access.")
    return allowed


def latest_event(connection, publication_id, key):
    return connection.execute(text(
        "SELECT e.*,r.batch_id FROM county_guide_events e JOIN county_guide_releases r ON r.id=e.release_id "
        "AND r.publication_id=e.publication_id WHERE e.publication_id=:p AND e.guide_key=:k ORDER BY e.id DESC LIMIT 1"
    ), {"p": publication_id, "k": key}).mappings().one_or_none()


def public_content(preview, source):
    """Explicitly copy public fields, never spread a private preview or receipt."""
    races = []
    for race in preview["races"]:
        if race["reviewStatusAtImport"] != "reviewed" or not race["recordedAcceptances"]:
            raise HTTPException(409, "The import is missing recorded human review evidence.")
        races.append({key: race[key] for key in (
            "id", "key", "ballotTitle", "governmentLevel", "jurisdictionName", "districtLabel",
            "seatsAvailable", "sourcePage", "pdfPageNumber", "candidates")})
        races[-1]["reviewedAt"] = max(datetime.fromisoformat(str(item["at"]).replace("Z", "+00:00"))
                                      for item in race["recordedAcceptances"])
    content = {key: preview[key] for key in ("county", "electionName", "electionDate", "raceCount", "candidateCount")}
    content["races"] = races
    content["source"] = {"title": source["title"], "publisherName": source["publisher_name"],
        "url": source["source_url"], "checksum": source["checksum_sha256"],
        "publishedAt": source["document_published_at"], "retrievedAt": source["retrieved_at"]}
    return GuideContent.model_validate(content).model_dump(mode="json")


def prepare_release(connection, publication_id, batch_id):
    batch = batch_row(connection, publication_id, batch_id, current=True)
    if not batch["imported"] or not batch.get("review_snapshot"):
        raise HTTPException(409, "Import the reviewed county with its saved review receipt before publishing.")
    # Keep reviewer eligibility stable until this transaction finishes; account
    # revocation must not race the review check and release insertion.
    connection.execute(text("SELECT id FROM editorial_users WHERE publication_id=:p ORDER BY id FOR SHARE"),
                       {"p": publication_id}).all()
    try:
        # Reuse existing content/active-reviewer/shared-coverage checks. This does
        # not create another review or mark any source newly verified.
        require_reviewed_manifest(connection, publication_id, batch["manifest"])
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    source = connection.execute(text(
        "SELECT d.* FROM documents d JOIN authority_source_registry s ON s.id=d.authority_source_registry_id "
        "JOIN election_authorities a ON a.id=s.authority_id AND a.publication_id=d.publication_id "
        "WHERE d.id=:d AND d.publication_id=:p AND d.is_authoritative AND d.source_type='official_document' "
        "AND a.status='active' AND s.approval_status='approved' AND s.permitted_use IN ('private_retention','public_copy') "
        "FOR SHARE OF d,s,a"
    ), {"d": batch["document_id"], "p": publication_id}).mappings().one_or_none()
    if source is None:
        raise HTTPException(409, "The official source no longer has active approval for this factual use.")
    expected_source = batch["manifest"]["sourceDocument"]
    if source["source_url"] != expected_source["sourceUrl"] or source["checksum_sha256"] != expected_source["checksumSha256"]:
        raise HTTPException(409, "The registered source identity no longer matches the reviewed import.")
    preview = guide_preview(connection, publication_id, batch_id)
    try:
        payload = public_content(preview, source)
    except (ValidationError, ValueError) as error:
        raise HTTPException(409, "The public source metadata or review dates need reconciliation.") from error
    basis = content_hash({"batch": str(batch_id), "content": payload, "receipt": batch["review_snapshot"]})
    return batch, payload, basis


def publication_status(connection, user, batch_id):
    lock_publication(connection, user["publication_id"])
    batch = batch_row(connection, user["publication_id"], batch_id)
    event = latest_event(connection, user["publication_id"], batch["batch_key"])
    blockers, basis = [], None
    try:
        _, _, basis = prepare_release(connection, user["publication_id"], batch_id)
    except HTTPException as error:
        if error.status_code != 409:
            raise
        blockers.append({"code": "content_not_ready", "message": error.detail})
    return {"batchId": str(batch_id), "canPublish": publisher_allowed(connection, user),
        "contentReady": not blockers, "blockers": blockers, "basisHash": basis,
        "currentEventId": event["id"] if event else None,
        "currentReleaseId": event["release_id"] if event else None,
        "publishedBatchId": event["batch_id"] if event and event["action"] == "publish" else None,
        "state": "published" if event and event["action"] == "publish" else "withdrawn" if event else "unpublished"}


def publish_guide(connection, user, batch_id, basis_hash, expected_event_id):
    lock_publication(connection, user["publication_id"])
    # Check existence/scope before privilege errors to keep foreign IDs hidden.
    batch = batch_row(connection, user["publication_id"], batch_id, current=True)
    publisher_allowed(connection, user, required=True)
    event = latest_event(connection, user["publication_id"], batch["batch_key"])
    if (event["id"] if event else None) != expected_event_id:
        raise HTTPException(409, "Publication state changed. Refresh before publishing; nothing was changed.")
    batch, payload, actual_basis = prepare_release(connection, user["publication_id"], batch_id)
    if actual_basis != basis_hash:
        raise HTTPException(409, "The content or evidence changed. Refresh the preview before publishing.")
    if event and event["action"] == "publish" and str(event["batch_id"]) == str(batch_id):
        raise HTTPException(409, "This revision is already published.")
    try:
        # Verify the privately retained evidence still exists and matches its
        # content-addressed checksum. Never fetch it again or expose its bytes.
        retained = document_store_from_environment().read_bytes(batch["storage_key"])
        if hashlib.sha256(retained).hexdigest() != payload["source"]["checksum"]:
            raise DocumentStorageError("Retained evidence does not match the public source checksum.")
    except (DocumentStorageError, OSError, TypeError) as error:
        raise HTTPException(503, "The retained source is missing or failed its integrity check. Restore it before publication.") from error
    release_id = uuid4()
    connection.execute(text(
        "INSERT INTO county_guide_releases(id,publication_id,guide_key,batch_id,actor_id,payload,evidence_hash) "
        "VALUES(:id,:p,:k,:b,:u,CAST(:payload AS jsonb),:h)"
    ), {"id": release_id, "p": user["publication_id"], "k": batch["batch_key"], "b": batch_id,
        "u": user["id"], "payload": json.dumps(payload), "h": actual_basis})
    connection.execute(text(
        "INSERT INTO county_guide_events(publication_id,guide_key,release_id,actor_id,action) VALUES(:p,:k,:r,:u,'publish')"
    ), {"p": user["publication_id"], "k": batch["batch_key"], "r": release_id, "u": user["id"]})
    return {"status": "published", "releaseId": str(release_id)}


def withdraw_guide(connection, user, release_id, expected_event_id, reason):
    lock_publication(connection, user["publication_id"])
    release = connection.execute(text(
        "SELECT guide_key FROM county_guide_releases WHERE id=:r AND publication_id=:p"
    ), {"r": release_id, "p": user["publication_id"]}).mappings().one_or_none()
    if release is None:
        raise HTTPException(404, "Guide release was not found.")
    publisher_allowed(connection, user, required=True)
    if not reason.strip():
        raise HTTPException(422, "Add a brief private reason for taking the guide offline.")
    event = latest_event(connection, user["publication_id"], release["guide_key"])
    if not event or event["id"] != expected_event_id or str(event["release_id"]) != str(release_id) or event["action"] != "publish":
        raise HTTPException(409, "This release is no longer the live guide. Refresh before withdrawing.")
    connection.execute(text(
        "INSERT INTO county_guide_events(publication_id,guide_key,release_id,actor_id,action,note) "
        "VALUES(:p,:k,:r,:u,'withdraw',:n)"
    ), {"p": user["publication_id"], "k": release["guide_key"], "r": release_id, "u": user["id"], "n": reason.strip()})
    return {"status": "withdrawn"}


def managed_releases(connection, publication_id):
    # Deliberately independent of current drafts, canonical joins and source
    # approval. A publisher must still be able to withdraw a problematic guide.
    rows = connection.execute(text(
        "SELECT r.batch_id,r.id,r.payload->>'county' AS county,e.created_at FROM county_guide_events e "
        "JOIN county_guide_releases r ON r.id=e.release_id AND r.publication_id=e.publication_id "
        "WHERE e.publication_id=:p AND e.action='publish' AND NOT EXISTS "
        "(SELECT 1 FROM county_guide_events n WHERE n.publication_id=e.publication_id "
        "AND n.guide_key=e.guide_key AND n.id>e.id) ORDER BY e.created_at DESC LIMIT 100"
    ), {"p": publication_id}).mappings().all()
    return [{"batchId": row["batch_id"], "releaseId": row["id"], "county": row["county"],
             "publishedAt": row["created_at"]} for row in rows]


PUBLIC_SELECT = """
    SELECT r.id,r.payload,e.created_at AS published_at FROM county_guide_events e
    JOIN county_guide_releases r ON r.id=e.release_id AND r.publication_id=e.publication_id
    JOIN publications p ON p.id=r.publication_id JOIN organizations o ON o.id=p.organization_id
    JOIN editorial_batches b ON b.id=r.batch_id AND b.publication_id=r.publication_id
    JOIN documents d ON d.id=b.document_id AND d.publication_id=b.publication_id
    JOIN authority_source_registry s ON s.id=d.authority_source_registry_id
    JOIN election_authorities a ON a.id=s.authority_id AND a.publication_id=d.publication_id
    WHERE o.slug=:organization AND p.slug=:publication AND e.action='publish'
      AND NOT EXISTS(SELECT 1 FROM county_guide_events newer WHERE newer.publication_id=e.publication_id
          AND newer.guide_key=e.guide_key AND newer.id>e.id)
      AND s.approval_status='approved' AND s.permitted_use IN ('private_retention','public_copy')
      AND a.status='active' AND d.is_authoritative AND d.source_type='official_document'
      AND d.source_url=r.payload->'source'->>'url' AND d.checksum_sha256=r.payload->'source'->>'checksum'
"""


def public_scope():
    # Reuse the existing operator-controlled pilot scope, not a client tenant ID.
    return {"organization": os.getenv("BALLOT_BROWSE_ORGANIZATION_SLUG", "whats-on-my-ballot").strip(),
            "publication": os.getenv("BALLOT_BROWSE_PUBLICATION_SLUG", "copperas-cove").strip()}


def read_public_guide(connection, release_id):
    row = connection.execute(text(PUBLIC_SELECT + " AND r.id=:id"),
                             {**public_scope(), "id": release_id}).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "No published county guide is available at this link.")
    # Revalidate the allowlist even for stored payloads. Staff/source bytes are
    # never serialized from a generic DB row or joined canonical record.
    return PublicGuide(**GuideContent.model_validate(row["payload"]).model_dump(),
                       releaseId=row["id"], publishedAt=row["published_at"])


def list_public_guides(connection, *, offset, limit, county=None):
    # A directory filter, not a geographic or voter match. Keep the same public
    # scope/source/release gates; never search private drafts or infer a ZIP map.
    county_filter = " AND lower(btrim(r.payload->>'county'))=lower(btrim(:county))" if county is not None else ""
    rows = connection.execute(text(PUBLIC_SELECT + county_filter +
        " ORDER BY r.payload->>'electionDate' DESC,r.payload->>'county',r.id LIMIT :limit OFFSET :offset"),
        {**public_scope(), "limit": limit + 1, "offset": offset, **({"county": county} if county is not None else {})}).mappings().all()
    items = []
    for row in rows[:limit]:
        payload = GuideContent.model_validate(row["payload"])
        items.append(GuideSummary(releaseId=row["id"], publishedAt=row["published_at"], **{
            key: getattr(payload, key) for key in ("county", "electionName", "electionDate", "raceCount", "candidateCount")}))
    return {"items": items, "offset": offset, "limit": limit, "hasMore": len(rows) > limit}
