"""Read canonical imported facts, constrained to an authenticated publication.

The immutable intake and promotion receipt select the records and establish the
historical review context. Display labels come from canonical tables. Missing or
changed canonical records fail closed, never fall back to the extraction draft.
"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import text

from app.source_pages import pdf_page_number


IMPORT_SELECT = """
    SELECT b.id, b.version, b.manifest, b.document_id, p.review_snapshot,
           p.created_at AS imported_at, u.username AS imported_by,
           d.title AS source_title, d.source_url, d.checksum_sha256,
           NOT EXISTS (SELECT 1 FROM editorial_batches n
                       WHERE n.publication_id=b.publication_id AND n.batch_key=b.batch_key
                       AND n.version>b.version) AS is_current
    FROM editorial_batches b
    JOIN editorial_promotions p ON p.batch_id=b.id AND p.publication_id=b.publication_id
    JOIN documents d ON d.id=b.document_id AND d.publication_id=b.publication_id
    JOIN editorial_users u ON u.id=p.actor_id AND u.publication_id=b.publication_id
    WHERE b.publication_id=:publication
"""


def preview_summary(batch) -> dict:
    manifest = batch["manifest"]
    return {"batchId": str(batch["id"]), "county": manifest["county"], "revision": batch["version"],
            "electionName": manifest["election"]["name"], "electionDate": manifest["election"]["date"],
            "raceCount": len(manifest["races"]),
            "candidateCount": sum(len(r["candidates"]) for r in manifest["races"]),
            "importedAt": batch["imported_at"]}


def list_previews(connection, publication_id) -> list[dict]:
    # Do not present an older import as current if a replacement draft exists.
    batches = connection.execute(text(IMPORT_SELECT + """
        AND NOT EXISTS (SELECT 1 FROM editorial_batches n
                        WHERE n.publication_id=b.publication_id AND n.batch_key=b.batch_key
                        AND n.version>b.version)
        ORDER BY b.manifest->'election'->>'date' DESC, b.manifest->>'county', b.version DESC
        LIMIT 100
    """), {"publication": publication_id}).mappings().all()
    return [preview_summary(batch) for batch in batches]


def _mismatch():
    raise HTTPException(409, "Imported records or citations no longer match this certification receipt. "
                        "Return to the review workspace and ask the operator to reconcile the records.")


def assemble_preview(batch, rows) -> dict:
    """Join records to source order, without inventing a ballot order or review."""
    manifest = batch["manifest"]
    grouped = {}
    for row in rows:
        grouped.setdefault(row["race_key"], []).append(row)
    if set(grouped) != {race["key"] for race in manifest["races"]}:
        _mismatch()
    snapshot = batch["review_snapshot"]
    receipt = {race["key"]: race for race in snapshot["races"]} if snapshot else {}
    result = []
    for expected in manifest["races"]:
        records = grouped[expected["key"]]
        first = records[0]
        expected_fields = {"ballot_title": expected["ballotTitle"], "office_name": expected["ballotTitle"], "government_level": expected["governmentLevel"],
                           "jurisdiction_name": expected["jurisdictionName"], "district_label": expected.get("districtLabel"),
                           "seats_available": expected.get("seatsAvailable", 1)}
        if any(any(row[key] != value for key, value in expected_fields.items()) or row["race_id"] != first["race_id"]
               for row in records):
            _mismatch()
        # Include all candidates in the canonical race, even those with missing
        # citations, so partial joins cannot silently hide a discrepancy.
        canonical = {str(row["candidate_id"]): row for row in records}
        if len(canonical) != len(expected["candidates"]) or any(row["candidate_id"] is None for row in records):
            _mismatch()
        candidates = []
        for candidate in expected["candidates"]:
            matches = [row for row in canonical.values() if row["ballot_label"] == candidate["ballotLabel"]
                       and row["party_label"] == candidate["partyLabel"]]
            if len(matches) != 1:
                _mismatch()
            row = matches[0]
            if not any(item["candidate_id"] == row["candidate_id"] and item["source_page"] == expected["sourcePage"]
                       for item in records):
                _mismatch()
            candidates.append({"id": str(row["candidate_id"]), "ballotLabel": row["ballot_label"],
                               "partyLabel": row["party_label"]})
        recorded = receipt.get(expected["key"])
        if snapshot and (not recorded or recorded["reviewStatus"] != "reviewed" or
                         any(recorded.get(key) != value for key, value in expected.items())):
            _mismatch()
        acceptances = []
        if recorded:
            for decision in recorded["decisions"]:
                if decision["decision"] == "accepted":
                    acceptances.append({"kind": "local", "reviewer": decision["reviewer"], "at": decision["at"],
                        "decisionId": decision["originalDecisionId"], "county": manifest["county"],
                        "batchId": str(batch["id"]), "sourcePage": expected["sourcePage"],
                        "pdfPageNumber": pdf_page_number(batch["checksum_sha256"], expected["sourcePage"])})
            for shared in recorded["sharedReviews"]:
                acceptances.append({"kind": "shared", "reviewer": shared["reviewer"], "at": shared["at"],
                    "decisionId": shared["originalDecisionId"], "county": shared["county"], "batchId": shared["batchId"],
                    "sourcePage": shared["sourcePage"],
                    "pdfPageNumber": pdf_page_number(batch["checksum_sha256"], shared["sourcePage"])})
        result.append({"id": str(first["race_id"]), "key": expected["key"], "ballotTitle": first["ballot_title"],
            "governmentLevel": first["government_level"], "jurisdictionName": first["jurisdiction_name"],
            "districtLabel": first["district_label"], "seatsAvailable": first["seats_available"],
            "sourcePage": expected["sourcePage"], "pdfPageNumber": pdf_page_number(batch["checksum_sha256"], expected["sourcePage"]),
            "candidates": candidates, "reviewStatusAtImport": "reviewed" if recorded else "unavailable",
            "recordedAcceptances": acceptances})
    return {**preview_summary(batch), "current": batch["is_current"], "importedBy": batch["imported_by"],
            "countySourceConfirmedBy": snapshot.get("countySourceConfirmedBy") if snapshot else None,
            "reviewReceiptAvailable": bool(snapshot),
            "source": {"title": batch["source_title"], "url": batch["source_url"], "checksum": batch["checksum_sha256"]},
            "races": result}


def guide_preview(connection, publication_id, batch_id) -> dict:
    batch = connection.execute(text(IMPORT_SELECT + " AND b.id=:batch"),
                               {"publication": publication_id, "batch": batch_id}).mappings().one_or_none()
    if batch is None:
        # Draft, nonexistent and other-publication IDs deliberately look alike.
        raise HTTPException(404, "No imported certification preview is available for this batch.")
    manifest = batch["manifest"]
    election = manifest["election"]
    rows = connection.execute(text("""
        SELECT r.id AS race_id, r.external_identifier AS race_key, r.ballot_title,
               r.district_label, r.seats_available, o.name AS office_name, o.government_level, o.jurisdiction_name,
               c.id AS candidate_id, c.ballot_label, c.party_label, cs.source_page
        FROM elections e
        JOIN election_source_citations es ON es.election_id=e.id AND es.publication_id=e.publication_id
             AND es.document_id=:document AND es.evidence_role='candidate_certification'
        JOIN races r ON r.election_id=e.id AND r.publication_id=e.publication_id
        JOIN offices o ON o.id=r.office_id AND o.publication_id=r.publication_id
        LEFT JOIN candidates c ON c.race_id=r.id AND c.publication_id=r.publication_id
        LEFT JOIN candidate_source_citations cs ON cs.candidate_id=c.id AND cs.publication_id=c.publication_id
             AND cs.document_id=:document AND cs.evidence_role='candidate_certification'
        WHERE e.publication_id=:publication AND e.authority_name=:authority
          AND e.jurisdiction_name=:county AND e.election_date=:date AND e.election_type=:type
          AND r.external_identifier=ANY(:keys)
    """), {"publication": publication_id, "document": batch["document_id"], "authority": election["authorityName"],
           "county": manifest["county"], "date": date.fromisoformat(election["date"]), "type": election["type"],
           "keys": [race["key"] for race in manifest["races"]]}).mappings().all()
    return assemble_preview(batch, rows)
