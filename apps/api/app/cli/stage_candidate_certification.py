"""Validate and optionally promote official candidate-certification facts.

The default mode is a write-free review. ``--apply`` requires recorded human
review and promotes facts into draft canonical records, retaining every source citation;
it never creates or publishes a ballot version.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import date
import json
from pathlib import Path
import re
from typing import Any


SHA256 = re.compile(r"^[0-9a-f]{64}$")
KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PARTIES = {"Republican", "Democratic", "Libertarian", "Green", "Independent", "None listed"}


def _only(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{label} contains unsupported fields: {', '.join(sorted(unknown))}")


def _text(value: Any, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be a non-empty string of at most {maximum} characters")
    return value.strip()


def _key(value: Any, label: str) -> str:
    result = _text(value, label, 255)
    if not KEY.fullmatch(result):
        raise ValueError(f"{label} must be a lowercase hyphenated key")
    return result


def read_manifest(path: Path) -> dict[str, Any]:
    return validate_manifest(json.loads(path.read_text(encoding="utf-8")))


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Shared validation for file intake and field-corrected review drafts."""
    _only(manifest, {"schemaVersion", "status", "organizationSlug", "publicationSlug", "sourceDocument",
                     "election", "county", "races"}, "manifest")
    if manifest.get("schemaVersion") != 1 or manifest.get("status") != "staged":
        raise ValueError("candidate certification must use schemaVersion 1 and staged status")
    _key(manifest.get("organizationSlug"), "organizationSlug")
    _key(manifest.get("publicationSlug"), "publicationSlug")

    source = manifest.get("sourceDocument")
    if not isinstance(source, dict):
        raise ValueError("sourceDocument is required")
    _only(source, {"title", "publisherName", "sourceUrl", "checksumSha256", "contentLengthBytes",
                   "publishedAt", "retrievedAt", "retention", "publicAccess"}, "sourceDocument")
    for field in ("title", "publisherName", "publishedAt", "retrievedAt", "retention", "publicAccess"):
        _text(source.get(field), f"sourceDocument.{field}")
    if not str(source.get("sourceUrl", "")).startswith("https://"):
        raise ValueError("sourceDocument.sourceUrl must use HTTPS")
    if not SHA256.fullmatch(str(source.get("checksumSha256", ""))):
        raise ValueError("sourceDocument.checksumSha256 must be lowercase SHA-256")
    if not isinstance(source.get("contentLengthBytes"), int) or source["contentLengthBytes"] <= 0:
        raise ValueError("sourceDocument.contentLengthBytes must be positive")

    election = manifest.get("election")
    if not isinstance(election, dict):
        raise ValueError("election metadata is required")
    _only(election, {"name", "authorityName", "date", "type"}, "election")
    _text(election.get("name"), "election.name")
    _text(election.get("authorityName"), "election.authorityName")
    _text(election.get("type"), "election.type")
    try:
        date.fromisoformat(str(election.get("date")))
    except ValueError as error:
        raise ValueError("election.date must use YYYY-MM-DD") from error

    _text(manifest.get("county"), "county", 255)
    races = manifest.get("races")
    if not isinstance(races, list) or not races:
        raise ValueError("at least one certified race is required")
    race_keys: set[str] = set()
    for race in races:
        if not isinstance(race, dict):
            raise ValueError("races must contain objects")
        _only(race, {"key", "ballotTitle", "governmentLevel", "jurisdictionName", "districtLabel",
                     "seatsAvailable", "sourcePage", "candidates"}, "race")
        key = _key(race.get("key"), "race.key")
        if key in race_keys:
            raise ValueError(f"duplicate race key: {key}")
        race_keys.add(key)
        for field in ("ballotTitle", "governmentLevel", "jurisdictionName", "sourcePage"):
            _text(race.get(field), f"race {key}.{field}")
        seats = race.get("seatsAvailable", 1)
        if not isinstance(seats, int) or not 1 <= seats <= 100:
            raise ValueError(f"race {key}.seatsAvailable must be between 1 and 100")
        candidates = race.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError(f"race {key} requires at least one candidate")
        labels: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError(f"race {key} candidates must be objects")
            _only(candidate, {"ballotLabel", "partyLabel"}, f"race {key} candidate")
            label = _text(candidate.get("ballotLabel"), f"race {key} candidate.ballotLabel", 255)
            if label.casefold() in labels:
                raise ValueError(f"race {key} contains a duplicate candidate")
            labels.add(label.casefold())
            if candidate.get("partyLabel") not in PARTIES:
                raise ValueError(f"race {key} candidate has an unsupported partyLabel")
    return manifest


def summary(manifest: dict[str, Any]) -> str:
    candidate_count = sum(len(race["candidates"]) for race in manifest["races"])
    return (f"Validated staged certification for {manifest['county']}: "
            f"{len(manifest['races'])} race(s), {candidate_count} candidate(s)")


def apply_manifest(manifest: dict[str, Any], *, connection=None) -> dict[str, int]:
    """Promote reviewed certification facts to draft canonical records.

    The exact source document must already be registered as authoritative. The
    operation adds citations and never creates or publishes a ballot version.
    """
    from sqlalchemy import text
    from app.database import get_engine
    from app.editorial_review import require_reviewed_manifest

    counts = {"races": 0, "candidates": 0, "citations": 0}
    with (nullcontext(connection) if connection is not None else get_engine().begin()) as connection:
        publication_id = connection.execute(text(
            "SELECT p.id FROM organizations o JOIN publications p ON p.organization_id=o.id "
            "WHERE o.slug=:organization AND p.slug=:publication"
        ), {"organization": manifest["organizationSlug"], "publication": manifest["publicationSlug"]}).scalar_one_or_none()
        if publication_id is None:
            raise ValueError("manifest publication was not found")
        require_reviewed_manifest(connection, publication_id, manifest)
        source = manifest["sourceDocument"]
        document = connection.execute(text(
            "SELECT id FROM documents WHERE publication_id=:p AND checksum_sha256=:checksum "
            "AND source_url=:url AND source_type='official_document' AND is_authoritative=TRUE"
        ), {"p": publication_id, "checksum": source["checksumSha256"], "url": source["sourceUrl"]}).scalar_one_or_none()
        if document is None:
            raise ValueError("the checksum-matching authoritative source document is not registered")
        election = manifest["election"]
        election_id = connection.execute(text(
            "WITH inserted AS (INSERT INTO elections "
            "(id,publication_id,authority_name,jurisdiction_name,election_date,election_type,official_document_id) "
            "VALUES (gen_random_uuid(),:p,:authority,:county,:date,:type,:doc) "
            "ON CONFLICT ON CONSTRAINT uq_elections_publication_authority_date_type DO NOTHING RETURNING id) "
            "SELECT id FROM inserted UNION ALL SELECT id FROM elections WHERE publication_id=:p "
            "AND authority_name=:authority AND jurisdiction_name=:county AND election_date=:date AND election_type=:type LIMIT 1"
        ), {"p": publication_id, "authority": election["authorityName"], "county": manifest["county"],
            "date": date.fromisoformat(election["date"]), "type": election["type"], "doc": document}).scalar_one()
        connection.execute(text(
            "INSERT INTO election_source_citations (id,publication_id,election_id,document_id,evidence_role) "
            "VALUES (gen_random_uuid(),:p,:e,:doc,'candidate_certification') "
            "ON CONFLICT ON CONSTRAINT uq_election_source_citation DO NOTHING"
        ), {"p": publication_id, "e": election_id, "doc": document})
        for race in manifest["races"]:
            office_id = connection.execute(text(
                "WITH inserted AS (INSERT INTO offices (id,publication_id,name,government_level,jurisdiction_name) "
                "VALUES (gen_random_uuid(),:p,:name,:level,:jurisdiction) "
                "ON CONFLICT ON CONSTRAINT uq_offices_publication_name_jurisdiction DO NOTHING RETURNING id) "
                "SELECT id FROM inserted UNION ALL SELECT id FROM offices WHERE publication_id=:p "
                "AND name=:name AND jurisdiction_name=:jurisdiction LIMIT 1"
            ), {"p": publication_id, "name": race["ballotTitle"], "level": race["governmentLevel"],
                "jurisdiction": race["jurisdictionName"]}).scalar_one()
            stored_level = connection.execute(text("SELECT government_level FROM offices WHERE id=:id"),
                                              {"id": office_id}).scalar_one()
            if stored_level != race["governmentLevel"]:
                raise ValueError(f"existing office for {race['key']} differs from certification")
            race_id = connection.execute(text(
                "WITH inserted AS (INSERT INTO races "
                "(id,publication_id,election_id,office_id,external_identifier,district_label,ballot_title,seats_available) "
                "VALUES (gen_random_uuid(),:p,:e,:office,:key,:district,:title,:seats) "
                "ON CONFLICT (publication_id,election_id,external_identifier) WHERE external_identifier IS NOT NULL "
                "DO NOTHING RETURNING id) SELECT id FROM inserted UNION ALL SELECT id FROM races "
                "WHERE publication_id=:p AND election_id=:e AND external_identifier=:key LIMIT 1"
            ), {"p": publication_id, "e": election_id, "office": office_id, "key": race["key"],
                "district": race.get("districtLabel"), "title": race["ballotTitle"],
                "seats": race.get("seatsAvailable", 1)}).scalar_one()
            stored_race = connection.execute(text(
                "SELECT office_id,district_label,ballot_title,seats_available FROM races WHERE id=:id"
            ), {"id": race_id}).mappings().one()
            expected_race = {"office_id": office_id, "district_label": race.get("districtLabel"),
                             "ballot_title": race["ballotTitle"], "seats_available": race.get("seatsAvailable", 1)}
            if any(stored_race[key] != value for key, value in expected_race.items()):
                raise ValueError(f"existing race {race['key']} differs from certification")
            existing_names = set(connection.execute(text("SELECT canonical_name FROM candidates WHERE race_id=:r"),
                                                    {"r": race_id}).scalars())
            expected_names = {candidate["ballotLabel"] for candidate in race["candidates"]}
            if existing_names - expected_names:
                raise ValueError(f"existing candidate roster for {race['key']} differs from certification; resolve the correction first")
            counts["races"] += 1
            for candidate in race["candidates"]:
                label = candidate["ballotLabel"]
                candidate_id = connection.execute(text(
                    "WITH inserted AS (INSERT INTO candidates "
                    "(id,publication_id,race_id,candidate_document_id,canonical_name,ballot_label,party_label) "
                    "VALUES (gen_random_uuid(),:p,:r,:doc,:name,:label,:party) "
                    "ON CONFLICT ON CONSTRAINT uq_candidates_race_canonical_name DO NOTHING RETURNING id) "
                    "SELECT id FROM inserted UNION ALL SELECT id FROM candidates "
                    "WHERE race_id=:r AND canonical_name=:name LIMIT 1"
                ), {"p": publication_id, "r": race_id, "doc": document, "name": label, "label": label,
                    "party": candidate["partyLabel"]}).scalar_one()
                stored = connection.execute(text(
                    "SELECT ballot_label,party_label FROM candidates WHERE id=:id"
                ), {"id": candidate_id}).mappings().one()
                if stored["ballot_label"] != label or stored["party_label"] != candidate["partyLabel"]:
                    raise ValueError(f"existing candidate {label} differs from certification")
                connection.execute(text(
                    "INSERT INTO candidate_source_citations "
                    "(id,publication_id,candidate_id,document_id,source_page,evidence_role) "
                    "VALUES (gen_random_uuid(),:p,:candidate,:doc,:page,'candidate_certification') "
                    "ON CONFLICT ON CONSTRAINT uq_candidate_source_citation DO NOTHING"
                ), {"p": publication_id, "candidate": candidate_id, "doc": document, "page": race["sourcePage"]})
                counts["candidates"] += 1
                counts["citations"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a checksum-pinned candidate certification staging file")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    manifest = read_manifest(arguments.manifest)
    print(summary(manifest))
    if arguments.apply:
        print(f"Imported certified draft candidacies: {apply_manifest(manifest)}")
    else:
        print("Dry run only; no database writes were made")


if __name__ == "__main__":
    main()
