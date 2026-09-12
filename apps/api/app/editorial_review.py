"""Private draft intake and revision-bound review; no public publication operation."""

import hashlib
import json
from copy import deepcopy
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from app.source_pages import pdf_page_number
from app.shared_editorial_reviews import load_shared_pool, shared_evidence, review_basis_hash


def content_hash(manifest: dict) -> str:
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def lock_publication(connection, publication_id) -> None:
    # Serialize intake, decisions and promotion so a new revision cannot race approval.
    connection.execute(text("SELECT id FROM publications WHERE id=:p FOR UPDATE"), {"p": publication_id}).scalar_one()


def unchanged_race_keys(previous: dict, current: dict) -> set[str]:
    """Never carry approval across changed evidence/election context or a changed section."""
    if {k: v for k, v in previous.items() if k != "races"} != {k: v for k, v in current.items() if k != "races"}:
        return set()
    old = {r["key"]: r for r in previous["races"]}
    return {r["key"] for r in current["races"] if old.get(r["key"]) == r}


def stage_batch(connection, publication_id, document_id, manifest: dict, *, correction: bool = False) -> str:
    lock_publication(connection, publication_id)
    source = manifest["sourceDocument"]
    document = connection.execute(text(
        "SELECT d.id FROM documents d JOIN publications p ON p.id=d.publication_id "
        "JOIN organizations o ON o.id=p.organization_id WHERE d.id=:d AND d.publication_id=:p "
        "AND d.checksum_sha256=:h AND d.source_url=:url AND d.is_authoritative "
        "AND d.source_type='official_document' AND p.slug=:ps AND o.slug=:os"
    ), {"d": document_id, "p": publication_id, "h": source["checksumSha256"], "url": source["sourceUrl"],
        "ps": manifest["publicationSlug"], "os": manifest["organizationSlug"]}).scalar_one_or_none()
    if document is None:
        raise ValueError("The draft and registered source must belong to the same publication and match exactly.")
    key = f"{manifest['election']['date']}:{manifest['election']['type']}:{manifest['county']}"
    digest = content_hash(manifest)
    previous = connection.execute(text(
        "SELECT * FROM editorial_batches WHERE publication_id=:p AND batch_key=:k ORDER BY version DESC LIMIT 1"
    ), {"p": publication_id, "k": key}).mappings().one_or_none()
    if previous and previous["content_hash"] == digest:
        return str(previous["id"])
    if previous and not correction and (previous["intake_content_hash"] or previous["content_hash"]) == digest:
        # Running setup again must not revert staff corrections to the same input file.
        return str(previous["id"])
    intake_hash = (previous["intake_content_hash"] or previous["content_hash"]) if correction and previous else digest
    batch_id = str(connection.execute(text(
        "INSERT INTO editorial_batches(id,publication_id,batch_key,document_id,content_hash,manifest,required_reviewers,intake_content_hash) "
        "VALUES(gen_random_uuid(),:p,:k,:d,:h,CAST(:m AS jsonb),:required,:intake) RETURNING id"
    ), {"p": publication_id, "k": key, "d": document_id, "h": digest, "m": json.dumps(manifest),
        "required": previous["required_reviewers"] if previous else 1, "intake": intake_hash}).scalar_one())
    if previous:
        unchanged = unchanged_race_keys(previous["manifest"], manifest)
        same_source = previous["document_id"] == document_id or str(previous["document_id"]) == str(document_id)
        latest = connection.execute(text(
            "SELECT DISTINCT ON (race_key,reviewer_id) * FROM editorial_decisions WHERE batch_id=:b "
            "ORDER BY race_key,reviewer_id,id DESC"
        ), {"b": previous["id"]}).mappings().all()
        keys = {r["key"] for r in manifest["races"]}
        for decision in latest:
            # Unresolved flags remain visible even when the section changes.
            if same_source and (decision["race_key"] in unchanged or
                                (decision["decision"] == "flagged" and decision["race_key"] in keys)):
                connection.execute(text(
                    "INSERT INTO editorial_decisions(publication_id,batch_id,reviewer_id,race_key,decision,note,carried_from_decision_id) "
                    "VALUES(:p,:b,:u,:k,:d,:n,:origin)"
                ), {"p": publication_id, "b": batch_id, "u": decision["reviewer_id"], "k": decision["race_key"],
                    "d": decision["decision"], "n": decision["note"],
                    "origin": decision["carried_from_decision_id"] or decision["id"]})
    return batch_id


def batch_row(connection, publication_id, batch_id, *, current: bool = False):
    row = connection.execute(text(
        "SELECT b.*,d.title AS source_title,d.source_url,d.storage_key,d.checksum_sha256, "
        "EXISTS(SELECT 1 FROM editorial_promotions p WHERE p.batch_id=b.id) AS imported, "
        "(SELECT p.review_snapshot FROM editorial_promotions p WHERE p.batch_id=b.id) AS review_snapshot, "
        "NOT EXISTS(SELECT 1 FROM editorial_batches n WHERE n.publication_id=b.publication_id "
        "AND n.batch_key=b.batch_key AND n.version>b.version) AS is_current "
        "FROM editorial_batches b JOIN documents d ON d.id=b.document_id "
        "WHERE b.id=:id AND b.publication_id=:p"
    ), {"id": batch_id, "p": publication_id}).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "Review batch was not found.")
    if current and not row["is_current"]:
        raise HTTPException(409, "A newer draft is available. Open the latest review task.")
    return row


def race_reviews(connection, batch, *, live: bool = False) -> list[dict]:
    if not live and batch.get("review_snapshot"):
        return batch["review_snapshot"]["races"]
    decisions = connection.execute(text(
        "SELECT DISTINCT ON (d.race_key,d.reviewer_id) d.*,u.username,u.active, "
        "COALESCE(origin.created_at,d.created_at) AS reviewed_at "
        "FROM editorial_decisions d JOIN editorial_users u ON u.id=d.reviewer_id "
        "LEFT JOIN editorial_decisions origin ON origin.id=d.carried_from_decision_id "
        "WHERE d.batch_id=:id ORDER BY d.race_key,d.reviewer_id,d.id DESC"
    ), {"id": batch["id"]}).mappings().all()
    corrections = connection.execute(text(
        "SELECT c.*,u.username FROM editorial_corrections c JOIN editorial_users u ON u.id=c.actor_id "
        "JOIN editorial_batches revision ON revision.id=c.batch_id "
        "JOIN editorial_batches target_batch ON target_batch.id=:id "
        "WHERE c.publication_id=target_batch.publication_id AND revision.batch_key=target_batch.batch_key "
        "AND revision.document_id=target_batch.document_id "
        "AND revision.version<=target_batch.version ORDER BY c.id"
    ), {"id": batch["id"]}).mappings().all()
    # Imported receipts are historical, not an assertion that a new source or
    # new flag was reviewed. Older imports without receipts retain local scope.
    pool = load_shared_pool(connection, batch) if live or not batch.get("imported") else {}
    result = []
    for race in batch["manifest"]["races"]:
        relevant = [d for d in decisions if d["race_key"] == race["key"]]
        flags = [d for d in relevant if d["decision"] == "flagged"]
        accepted = [d for d in relevant if d["decision"] == "accepted" and d["active"]]
        shared, counties, blocked = shared_evidence(batch, race, relevant, pool)
        shared = [{**item, "pdfPageNumber": pdf_page_number(batch["checksum_sha256"], item["sourcePage"])} for item in shared]
        approval_count = len(accepted) + len(shared)
        status = "flagged" if flags else "reviewed" if approval_count >= batch["required_reviewers"] else "unreviewed"
        local_reviewed = not flags and len(accepted) >= batch["required_reviewers"]
        result.append({**race, "pdfPageNumber": pdf_page_number(batch["checksum_sha256"], race["sourcePage"]),
                       "reviewStatus": status, "approvalCount": approval_count,
                       "localApprovalCount": len(accepted), "countySourceReviewed": local_reviewed,
                       "sharedReviews": shared, "matchingCounties": counties, "sharedReviewBlockedReason": blocked,
                       "decisions": [{"decisionId": str(d["id"]),
                                      "originalDecisionId": str(d["carried_from_decision_id"] or d["id"]),
                                      "reviewer": d["username"], "decision": d["decision"], "note": d["note"],
                                      "at": d["reviewed_at"].isoformat(),
                                      "carriedForward": d["carried_from_decision_id"] is not None} for d in relevant],
                       "corrections": [{"reviewer": c["username"], "at": c["created_at"].isoformat(),
                                        "changes": c["changes"], "note": c["note"]}
                                       for c in corrections if c["race_key"] == race["key"]]})
    return result


def batch_detail(connection, publication_id, batch_id) -> dict:
    batch = batch_row(connection, publication_id, batch_id)
    races = race_reviews(connection, batch)
    shared_count = sum(r["reviewStatus"] == "reviewed" and not r["countySourceReviewed"] for r in races)
    return {"id": str(batch["id"]), "county": batch["manifest"]["county"], "revision": batch["version"],
            "contentHash": batch["content_hash"], "election": batch["manifest"]["election"],
            "requiredReviewers": batch["required_reviewers"], "current": batch["is_current"],
            "imported": batch["imported"], "reviewedRaces": sum(r["reviewStatus"] == "reviewed" for r in races),
            "raceCount": len(races), "candidateCount": sum(len(r["candidates"]) for r in races),
            "sharedReviewedRaces": shared_count, "requiresCountyConfirmation": bool(shared_count and not batch["imported"]),
            "reviewBasisHash": review_basis_hash(batch, races),
            "countySourceConfirmedBy": (batch.get("review_snapshot") or {}).get("countySourceConfirmedBy"),
            "source": {"title": batch["source_title"], "url": batch["source_url"], "checksum": batch["checksum_sha256"]},
            "races": races}


def record_decision(connection, user: dict, batch_id: UUID, keys: list[str], decision: str, note: str) -> dict:
    lock_publication(connection, user["publication_id"])
    batch = batch_row(connection, user["publication_id"], batch_id, current=True)
    if batch["imported"]:
        raise HTTPException(409, "This revision was already imported. Create a corrected draft for further changes.")
    known = {r["key"] for r in batch["manifest"]["races"]}
    if not keys or len(set(keys)) != len(keys) or not set(keys) <= known:
        raise HTTPException(422, "Select distinct races from this review batch.")
    if decision not in {"accepted", "flagged"} or (decision == "flagged" and not note.strip()):
        raise HTTPException(422, "Flagged sections need a description of the problem.")
    for key in keys:
        connection.execute(text(
            "INSERT INTO editorial_decisions(publication_id,batch_id,reviewer_id,race_key,decision,note) "
            "VALUES(:p,:b,:u,:k,:d,:n)"
        ), {"p": user["publication_id"], "b": batch_id, "u": user["id"], "k": key, "d": decision, "n": note})
    return batch_detail(connection, user["publication_id"], batch_id)


def prepare_section_submission(manifest: dict, sections: list[dict]) -> tuple[dict, dict[str, list[dict]]]:
    """Validate all decisions/corrections before any write; only transcribed labels are editable."""
    from app.cli.stage_candidate_certification import PARTIES, validate_manifest

    corrected = deepcopy(manifest)
    races = {race["key"]: race for race in corrected["races"]}
    keys = [section["raceKey"] for section in sections]
    if not keys or len(set(keys)) != len(keys) or not set(keys) <= races.keys():
        raise ValueError("Choose distinct sections from the current review batch.")
    changes = {}
    for section in sections:
        corrections = section.get("corrections", [])
        if section["decision"] not in {"accepted", "flagged"}:
            raise ValueError("Choose Accept or Flag for each submitted section.")
        if corrections and section["decision"] != "flagged":
            raise ValueError("Corrected sections must be flagged and accepted in a later submission.")
        if section["decision"] == "flagged" and not corrections and not section.get("note", "").strip():
            raise ValueError("Explain each flagged section or provide a transcription correction.")
        race = races[section["raceKey"]]
        touched = set()
        for change in corrections:
            field, index = change["field"], change.get("candidateIndex")
            if (field, index) in touched:
                raise ValueError("A field can only be corrected once in a submission.")
            touched.add((field, index))
            if field == "ballotTitle" and index is None:
                target = race
            elif field in {"ballotLabel", "partyLabel"} and type(index) is int and 0 <= index < len(race["candidates"]):
                target = race["candidates"][index]
            else:
                raise ValueError("Correct only an office title, candidate name or party in the selected section.")
            value = change["value"].strip()
            if not value or len(value) > 255:
                raise ValueError("Corrected labels must contain 1–255 characters.")
            if field == "partyLabel" and value not in PARTIES:
                raise ValueError("Choose a supported party label exactly as listed by the source.")
            before = target[field]
            if before == value:
                raise ValueError("A correction must change the existing value; remove unchanged corrections.")
            target[field] = value
            changes.setdefault(section["raceKey"], []).append({
                "field": field, "candidateIndex": index, "before": before, "after": value,
            })
    validate_manifest(corrected)
    return corrected, changes


def submit_sections(connection, user: dict, batch_id: UUID, sections: list[dict]) -> dict:
    """One transaction for mixed section decisions and a correction revision, if needed."""
    lock_publication(connection, user["publication_id"])
    batch = batch_row(connection, user["publication_id"], batch_id, current=True)
    if batch["imported"]:
        raise HTTPException(409, "This revision was imported. Canonical corrections require a separate workflow.")
    try:
        corrected, changes = prepare_section_submission(batch["manifest"], sections)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    new_id = stage_batch(connection, user["publication_id"], batch["document_id"], corrected, correction=True) if changes else batch_id
    for section in sections:
        key = section["raceKey"]
        note = section.get("note", "").strip()
        if key in changes:
            note = note or "Transcription corrected to match the cited source; corrected section needs acceptance."
            connection.execute(text(
                "INSERT INTO editorial_corrections(publication_id,parent_batch_id,batch_id,race_key,actor_id,changes,note) "
                "VALUES(:p,:parent,:b,:k,:u,CAST(:changes AS jsonb),:note)"
            ), {"p": user["publication_id"], "parent": batch_id, "b": new_id, "k": key, "u": user["id"],
                "changes": json.dumps(changes[key]), "note": note})
        connection.execute(text(
            "INSERT INTO editorial_decisions(publication_id,batch_id,reviewer_id,race_key,decision,note) VALUES(:p,:b,:u,:k,:d,:n)"
        ), {"p": user["publication_id"], "b": new_id, "u": user["id"], "k": key, "d": section["decision"], "n": note})
    return batch_detail(connection, user["publication_id"], new_id)


def require_reviewed_manifest(connection, publication_id, manifest: dict):
    lock_publication(connection, publication_id)
    row = connection.execute(text(
        "SELECT id FROM editorial_batches WHERE publication_id=:p AND content_hash=:h ORDER BY version DESC LIMIT 1"
    ), {"p": publication_id, "h": content_hash(manifest)}).scalar_one_or_none()
    if row is None:
        raise ValueError("Load this manifest into the editorial workspace and review it before canonical import.")
    batch = batch_row(connection, publication_id, row, current=True)
    disposition = connection.execute(text(
        "SELECT s.approval_status,s.permitted_use FROM documents d "
        "JOIN authority_source_registry s ON s.id=d.authority_source_registry_id WHERE d.id=:d"
    ), {"d": batch["document_id"]}).mappings().one_or_none()
    if disposition is None or disposition["approval_status"] != "approved" or disposition["permitted_use"] not in {"private_retention", "public_copy"}:
        raise ValueError("The source no longer has an active private-retention approval.")
    races = race_reviews(connection, batch, live=True)
    if any(r["reviewStatus"] != "reviewed" for r in races):
        raise ValueError("This draft still has unreviewed or flagged races. Continue in the editorial workspace.")
    if any(not r["countySourceReviewed"] for r in races):
        receipt = batch.get("review_snapshot") or {}
        if not receipt.get("countySourceConfirmedBy") or receipt.get("basisHash") != review_basis_hash(batch, races):
            raise ValueError("Shared content reviews do not check this county's source pages. Confirm county coverage in the workspace before import.")
    return batch


def promote(connection, user: dict, batch_id, *, confirmed_county_coverage: bool = False, expected_basis: str | None = None) -> dict:
    from app.cli.stage_candidate_certification import apply_manifest

    lock_publication(connection, user["publication_id"])
    batch = batch_row(connection, user["publication_id"], batch_id, current=True)
    if batch["imported"]:
        return batch_detail(connection, user["publication_id"], batch_id)
    races = race_reviews(connection, batch, live=True)
    basis = review_basis_hash(batch, races)
    if expected_basis is not None and expected_basis != basis:
        raise HTTPException(409, "Review evidence changed. Reopen the county task before confirming import.")
    if any(r["reviewStatus"] != "reviewed" for r in races):
        raise HTTPException(409, "This county still has unreviewed or flagged race content.")
    shared = any(not r["countySourceReviewed"] for r in races)
    if shared and (not confirmed_county_coverage or expected_basis != basis):
        raise HTTPException(409, "Confirm this county's listed contests against its source pages before importing shared content reviews.")
    # The receipt and canonical import commit together or both roll back. It
    # records who checked county coverage, separately from whose content was reused.
    receipt = {"races": races, "basisHash": basis,
               "countySourceConfirmedBy": user["username"] if shared else None}
    connection.execute(text(
        "INSERT INTO editorial_promotions(batch_id,publication_id,actor_id,review_snapshot) VALUES(:b,:p,:u,CAST(:snapshot AS jsonb))"
    ), {"b": batch_id, "p": user["publication_id"], "u": user["id"], "snapshot": json.dumps(receipt)})
    try:
        apply_manifest(batch["manifest"], connection=connection)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return batch_detail(connection, user["publication_id"], batch_id)
