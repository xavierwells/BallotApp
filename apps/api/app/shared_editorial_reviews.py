"""Reuse human content checks, never invent checks of a second county's PDF page."""

import hashlib
import json

from sqlalchemy import text


def fingerprint(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def race_identity(manifest: dict, race: dict) -> str:
    # County election administrators differ. The certified election, office key,
    # jurisdiction and district must not. Local/county names lack global IDs, so
    # automatic cross-county reuse is initially limited to state/federal races.
    return fingerprint({
        "organization": manifest["organizationSlug"], "publication": manifest["publicationSlug"],
        "source": {k: v for k, v in manifest["sourceDocument"].items() if k != "retrievedAt"},
        "election": {k: v for k, v in manifest["election"].items() if k != "authorityName"},
        "key": race["key"], "level": race["governmentLevel"],
        "jurisdiction": race["jurisdictionName"], "district": race.get("districtLabel"),
        "county": None if race["governmentLevel"] in {"state", "federal"} else manifest["county"],
    })


def race_content(race: dict) -> str:
    content = {k: v for k, v in race.items() if k not in {"sourcePage", "candidates"}}
    content.setdefault("districtLabel", None)
    content.setdefault("seatsAvailable", 1)
    # Order on a county page is local evidence, not part of shared name/party review.
    content["candidates"] = sorted(race["candidates"], key=lambda c: (c["ballotLabel"], c["partyLabel"]))
    return fingerprint(content)


def load_shared_pool(connection, batch) -> dict[str, list[dict]]:
    """Current direct decisions only: a derived shared review can never be a donor."""
    current = (
        "b.publication_id=:p AND b.document_id=:doc AND NOT EXISTS "
        "(SELECT 1 FROM editorial_batches newer WHERE newer.publication_id=b.publication_id "
        "AND newer.batch_key=b.batch_key AND newer.version>b.version)"
    )
    params = {"p": batch["publication_id"], "doc": batch["document_id"]}
    batches = connection.execute(text("SELECT b.* FROM editorial_batches b WHERE " + current), params).mappings().all()
    decisions = connection.execute(text(
        "SELECT DISTINCT ON (d.batch_id,d.race_key,d.reviewer_id) d.*,u.username,u.active, "
        "COALESCE(origin.created_at,d.created_at) AS reviewed_at "
        "FROM editorial_decisions d JOIN editorial_batches b ON b.id=d.batch_id "
        "JOIN editorial_users u ON u.id=d.reviewer_id AND u.publication_id=d.publication_id "
        "LEFT JOIN editorial_decisions origin ON origin.id=d.carried_from_decision_id "
        "WHERE " + current + " ORDER BY d.batch_id,d.race_key,d.reviewer_id,d.id DESC"
    ), params).mappings().all()
    by_section = {}
    for decision in decisions:
        by_section.setdefault((str(decision["batch_id"]), decision["race_key"]), []).append(decision)
    pool = {}
    for source in batches:
        for race in source["manifest"]["races"]:
            entry = {"batchId": str(source["id"]), "county": source["manifest"]["county"], "race": race,
                     "content": race_content(race), "decisions": by_section.get((str(source["id"]), race["key"]), [])}
            pool.setdefault(race_identity(source["manifest"], race), []).append(entry)
    return pool


def shared_evidence(batch, race: dict, local_decisions: list, pool: dict) -> tuple[list, list, str | None]:
    if not pool:
        return [], [], None
    group = pool.get(race_identity(batch["manifest"], race), [])
    others = [entry for entry in group if entry["county"] != batch["manifest"]["county"]]
    counties = sorted({entry["county"] for entry in others})
    if not others:
        return [], [], None
    if any(entry["content"] != race_content(race) for entry in group):
        return [], counties, "County entries differ. Shared review is paused; compare and review the differing content."
    if any(d["decision"] == "flagged" for entry in group for d in entry["decisions"]):
        return [], counties, "An unresolved flag exists in a matching county entry. Shared review is paused."
    # A local decision is never overwritten by an acceptance from another county.
    seen = {str(d["reviewer_id"]) for d in local_decisions}
    evidence = []
    for entry in sorted(others, key=lambda e: (e["county"], e["batchId"])):
        for decision in entry["decisions"]:
            reviewer_id = str(decision["reviewer_id"])
            if decision["decision"] != "accepted" or not decision["active"] or reviewer_id in seen:
                continue
            seen.add(reviewer_id)
            evidence.append({"decisionId": str(decision["id"]),
                "originalDecisionId": str(decision["carried_from_decision_id"] or decision["id"]),
                "reviewer": decision["username"], "at": decision["reviewed_at"].isoformat(),
                "county": entry["county"], "batchId": entry["batchId"], "raceKey": entry["race"]["key"],
                "sourcePage": entry["race"]["sourcePage"]})
    return evidence, counties, None


def review_basis_hash(batch, races: list[dict]) -> str:
    return fingerprint({"batchId": str(batch["id"]), "contentHash": batch["content_hash"],
        "requiredReviewers": batch["required_reviewers"], "races": races})
