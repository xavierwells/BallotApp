"""Validate and optionally import a source-backed official ballot manifest as draft data."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from typing import Any

from sqlalchemy import text

from app.database import get_engine


SHA256 = re.compile(r"^[0-9a-f]{64}$")
KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _only(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{label} contains unsupported fields: {', '.join(sorted(unknown))}")


def _nonempty(value: Any, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label} must be a non-empty string of at most {maximum} characters")
    return value.strip()


def _key(value: Any, label: str) -> str:
    value = _nonempty(value, label, 255)
    if not KEY.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase hyphenated key")
    return value


def read_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1:
        raise ValueError("official ballot manifest must use schemaVersion 1")
    _only(manifest, {"schemaVersion", "organizationSlug", "publicationSlug", "sourceDocument",
        "election", "races", "propositions", "ballotVersions"}, "manifest")
    for field in ("organizationSlug", "publicationSlug"):
        _key(manifest.get(field), field)
    source = manifest.get("sourceDocument")
    if not isinstance(source, dict) or not SHA256.fullmatch(str(source.get("checksumSha256", ""))):
        raise ValueError("sourceDocument requires a lowercase SHA-256 checksum")
    _only(source, {"checksumSha256", "sourceUrl"}, "sourceDocument")
    if not str(source.get("sourceUrl", "")).startswith("https://"):
        raise ValueError("sourceDocument requires an HTTPS sourceUrl")

    election = manifest.get("election")
    if not isinstance(election, dict):
        raise ValueError("official ballot manifest requires election metadata")
    _only(election, {"authorityName", "jurisdictionName", "electionDate", "electionType"}, "election")
    for field in ("authorityName", "jurisdictionName", "electionType"):
        _nonempty(election.get(field), f"election.{field}", 255)
    try:
        date.fromisoformat(str(election.get("electionDate")))
    except ValueError as error:
        raise ValueError("election.electionDate must use YYYY-MM-DD") from error

    races = manifest.get("races")
    propositions = manifest.get("propositions", [])
    ballots = manifest.get("ballotVersions")
    if not isinstance(races, list) or not isinstance(propositions, list) or not isinstance(ballots, list) or not ballots:
        raise ValueError("manifest requires races/propositions lists and at least one ballot version")

    race_keys: set[str] = set()
    for race in races:
        key = _key(race.get("key") if isinstance(race, dict) else None, "race.key")
        if key in race_keys:
            raise ValueError(f"duplicate race key: {key}")
        _only(race, {"key", "office", "districtLabel", "ballotTitle", "seatsAvailable", "candidates"}, f"race {key}")
        race_keys.add(key)
        office = race.get("office")
        if not isinstance(office, dict):
            raise ValueError(f"race {key} requires office metadata")
        _only(office, {"name", "governmentLevel", "jurisdictionName", "termDescription"}, f"race {key} office")
        for field in ("name", "governmentLevel", "jurisdictionName"):
            _nonempty(office.get(field), f"race {key} office.{field}", 255)
        _nonempty(race.get("ballotTitle"), f"race {key} ballotTitle")
        seats = race.get("seatsAvailable", 1)
        if not isinstance(seats, int) or not 1 <= seats <= 100:
            raise ValueError(f"race {key} seatsAvailable must be between 1 and 100")
        candidates = race.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError(f"race {key} requires at least one official-ballot candidate")
        names: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError(f"race {key} candidates must be objects")
            _only(candidate, {"canonicalName", "ballotLabel"}, f"race {key} candidate")
            name = _nonempty(candidate.get("canonicalName"), f"race {key} candidate canonicalName", 255)
            if name.casefold() in names:
                raise ValueError(f"race {key} has a duplicate candidate name")
            names.add(name.casefold())
            _nonempty(candidate.get("ballotLabel", name), f"race {key} candidate ballotLabel", 255)

    proposition_keys: set[str] = set()
    for proposition in propositions:
        key = _key(proposition.get("key") if isinstance(proposition, dict) else None, "proposition.key")
        if key in proposition_keys:
            raise ValueError(f"duplicate proposition key: {key}")
        _only(proposition, {"key", "ballotTitle", "officialText", "sourcePage"}, f"proposition {key}")
        proposition_keys.add(key)
        for field in ("ballotTitle", "officialText", "sourcePage"):
            _nonempty(proposition.get(field), f"proposition {key} {field}", 20_000)

    ballot_ids: set[str] = set()
    for ballot in ballots:
        identifier = _key(ballot.get("externalIdentifier") if isinstance(ballot, dict) else None, "ballot externalIdentifier")
        if identifier in ballot_ids:
            raise ValueError(f"duplicate ballot externalIdentifier: {identifier}")
        _only(ballot, {"externalIdentifier", "items", "geographicRequirements"}, f"ballot {identifier}")
        ballot_ids.add(identifier)
        items = ballot.get("items")
        requirements = ballot.get("geographicRequirements")
        if not isinstance(items, list) or not items:
            raise ValueError(f"ballot {identifier} requires at least one item")
        if [item.get("sequence") for item in items if isinstance(item, dict)] != list(range(1, len(items) + 1)):
            raise ValueError(f"ballot {identifier} items must have consecutive sequences starting at 1")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"ballot {identifier} items must be objects")
            _only(item, {"sequence", "type", "key", "sourcePage"}, f"ballot {identifier} item")
            item_type = item.get("type")
            key = item.get("key")
            if item_type == "race" and key not in race_keys:
                raise ValueError(f"ballot {identifier} references unknown race {key!r}")
            if item_type == "proposition" and key not in proposition_keys:
                raise ValueError(f"ballot {identifier} references unknown proposition {key!r}")
            if item_type not in {"race", "proposition"}:
                raise ValueError(f"ballot {identifier} has unsupported item type")
            _nonempty(item.get("sourcePage"), f"ballot {identifier} item sourcePage", 80)
        if not isinstance(requirements, list) or not requirements:
            raise ValueError(f"ballot {identifier} requires verified geographic requirements")
        pairs: set[tuple[str, str]] = set()
        for requirement in requirements:
            if not isinstance(requirement, dict):
                raise ValueError(f"ballot {identifier} geographic requirements must be objects")
            _only(requirement, {"authoritySlug", "areaSlug", "verifiedByReference"}, f"ballot {identifier} requirement")
            pair = (_key(requirement.get("authoritySlug"), "authoritySlug"), _key(requirement.get("areaSlug"), "areaSlug"))
            if pair in pairs:
                raise ValueError(f"ballot {identifier} has a duplicate geographic requirement")
            pairs.add(pair)
            _nonempty(requirement.get("verifiedByReference"), "verifiedByReference", 128)
    return manifest


def _same(row: Any, expected: dict[str, Any], label: str) -> None:
    if any(row[key] != value for key, value in expected.items()):
        raise ValueError(f"existing {label} differs from the pinned manifest")


def apply_manifest(manifest: dict[str, Any]) -> dict[str, int]:
    """Apply one fully validated manifest transactionally; all ballot versions remain draft."""
    counts = {"races": 0, "candidates": 0, "propositions": 0, "ballotVersions": 0, "items": 0}
    with get_engine().begin() as connection:
        publication_id = connection.execute(text(
            "SELECT p.id FROM organizations o JOIN publications p ON p.organization_id = o.id "
            "WHERE o.slug=:organization AND p.slug=:publication"
        ), {"organization": manifest["organizationSlug"], "publication": manifest["publicationSlug"]}).scalar_one_or_none()
        if publication_id is None:
            raise ValueError("manifest publication was not found")
        source = manifest["sourceDocument"]
        document = connection.execute(text(
            "SELECT id, source_url, retrieved_at FROM documents WHERE publication_id=:publication_id "
            "AND checksum_sha256=:checksum AND source_type='official_document' AND is_authoritative=TRUE"
        ), {"publication_id": publication_id, "checksum": source["checksumSha256"]}).mappings().one_or_none()
        if document is None or document["source_url"] != source["sourceUrl"]:
            raise ValueError("the exact authoritative source document is not registered for this publication")
        document_id = document["id"]
        election = manifest["election"]
        election_id = connection.execute(text(
            "WITH inserted AS (INSERT INTO elections (id,publication_id,authority_name,jurisdiction_name,election_date,election_type,official_document_id) "
            "VALUES (gen_random_uuid(),:p,:a,:j,:d,:t,:doc) ON CONFLICT ON CONSTRAINT uq_elections_publication_authority_date_type DO NOTHING RETURNING id) "
            "SELECT id FROM inserted UNION ALL SELECT id FROM elections WHERE publication_id=:p AND authority_name=:a "
            "AND jurisdiction_name=:j AND election_date=:d AND election_type=:t LIMIT 1"
        ), {"p": publication_id, "a": election["authorityName"], "j": election["jurisdictionName"],
            "d": date.fromisoformat(election["electionDate"]), "t": election["electionType"], "doc": document_id}).scalar_one()
        existing_doc = connection.execute(text("SELECT official_document_id FROM elections WHERE id=:id"), {"id": election_id}).scalar_one()
        if existing_doc != document_id:
            raise ValueError("existing election differs from the pinned source document")

        race_ids: dict[str, Any] = {}
        for race in manifest["races"]:
            office = race["office"]
            office_id = connection.execute(text(
                "WITH inserted AS (INSERT INTO offices (id,publication_id,name,government_level,jurisdiction_name,term_description) "
                "VALUES (gen_random_uuid(),:p,:n,:g,:j,:term) ON CONFLICT ON CONSTRAINT uq_offices_publication_name_jurisdiction DO NOTHING RETURNING id) "
                "SELECT id FROM inserted UNION ALL SELECT id FROM offices WHERE publication_id=:p AND name=:n AND jurisdiction_name=:j LIMIT 1"
            ), {"p": publication_id, "n": office["name"], "g": office["governmentLevel"], "j": office["jurisdictionName"], "term": office.get("termDescription")}).scalar_one()
            office_row = connection.execute(text("SELECT government_level,term_description FROM offices WHERE id=:id"), {"id": office_id}).mappings().one()
            _same(office_row, {"government_level": office["governmentLevel"], "term_description": office.get("termDescription")}, "office")
            race_id = connection.execute(text(
                "WITH inserted AS (INSERT INTO races (id,publication_id,election_id,office_id,external_identifier,district_label,ballot_title,seats_available) "
                "VALUES (gen_random_uuid(),:p,:e,:o,:key,:district,:title,:seats) ON CONFLICT (publication_id,election_id,external_identifier) WHERE external_identifier IS NOT NULL DO NOTHING RETURNING id) "
                "SELECT id FROM inserted UNION ALL SELECT id FROM races WHERE publication_id=:p AND election_id=:e AND external_identifier=:key LIMIT 1"
            ), {"p": publication_id, "e": election_id, "o": office_id, "key": race["key"], "district": race.get("districtLabel"), "title": race["ballotTitle"], "seats": race.get("seatsAvailable", 1)}).scalar_one()
            race_row = connection.execute(text("SELECT office_id,district_label,ballot_title,seats_available FROM races WHERE id=:id"), {"id": race_id}).mappings().one()
            _same(race_row, {"office_id": office_id, "district_label": race.get("districtLabel"), "ballot_title": race["ballotTitle"], "seats_available": race.get("seatsAvailable", 1)}, f"race {race['key']}")
            race_ids[race["key"]] = race_id
            counts["races"] += 1
            for candidate in race["candidates"]:
                candidate_id = connection.execute(text(
                    "WITH inserted AS (INSERT INTO candidates (id,publication_id,race_id,candidate_document_id,canonical_name,ballot_label) "
                    "VALUES (gen_random_uuid(),:p,:r,:doc,:name,:label) ON CONFLICT ON CONSTRAINT uq_candidates_race_canonical_name DO NOTHING RETURNING id) "
                    "SELECT id FROM inserted UNION ALL SELECT id FROM candidates WHERE race_id=:r AND canonical_name=:name LIMIT 1"
                ), {"p": publication_id, "r": race_id, "doc": document_id, "name": candidate["canonicalName"], "label": candidate.get("ballotLabel", candidate["canonicalName"])}).scalar_one()
                candidate_row = connection.execute(text("SELECT candidate_document_id,ballot_label FROM candidates WHERE id=:id"), {"id": candidate_id}).mappings().one()
                _same(candidate_row, {"candidate_document_id": document_id, "ballot_label": candidate.get("ballotLabel", candidate["canonicalName"])}, "candidate")
                counts["candidates"] += 1
            candidate_count = connection.execute(text("SELECT COUNT(*) FROM candidates WHERE race_id=:r"), {"r": race_id}).scalar_one()
            if candidate_count != len(race["candidates"]):
                raise ValueError(f"existing race {race['key']} has candidates outside the pinned manifest")

        proposition_ids: dict[str, Any] = {}
        for proposition in manifest.get("propositions", []):
            proposition_id = connection.execute(text(
                "WITH inserted AS (INSERT INTO propositions (id,publication_id,election_id,official_document_id,external_identifier,ballot_title,official_text,source_page) "
                "VALUES (gen_random_uuid(),:p,:e,:doc,:key,:title,:body,:page) ON CONFLICT (publication_id,election_id,external_identifier) WHERE external_identifier IS NOT NULL DO NOTHING RETURNING id) "
                "SELECT id FROM inserted UNION ALL SELECT id FROM propositions WHERE publication_id=:p AND election_id=:e AND external_identifier=:key LIMIT 1"
            ), {"p": publication_id, "e": election_id, "doc": document_id, "key": proposition["key"], "title": proposition["ballotTitle"], "body": proposition["officialText"], "page": proposition["sourcePage"]}).scalar_one()
            proposition_row = connection.execute(text(
                "SELECT official_document_id,ballot_title,official_text,source_page FROM propositions WHERE id=:id"
            ), {"id": proposition_id}).mappings().one()
            _same(proposition_row, {"official_document_id": document_id, "ballot_title": proposition["ballotTitle"],
                "official_text": proposition["officialText"], "source_page": proposition["sourcePage"]}, f"proposition {proposition['key']}")
            proposition_ids[proposition["key"]] = proposition_id
            counts["propositions"] += 1

        for ballot in manifest["ballotVersions"]:
            ballot_id = connection.execute(text(
                "WITH inserted AS (INSERT INTO ballot_versions (id,publication_id,election_id,official_document_id,external_identifier,status,retrieved_at) "
                "VALUES (gen_random_uuid(),:p,:e,:doc,:key,'draft',:retrieved) ON CONFLICT (publication_id,election_id,external_identifier) WHERE external_identifier IS NOT NULL DO NOTHING RETURNING id) "
                "SELECT id FROM inserted UNION ALL SELECT id FROM ballot_versions WHERE publication_id=:p AND election_id=:e AND external_identifier=:key LIMIT 1"
            ), {"p": publication_id, "e": election_id, "doc": document_id, "key": ballot["externalIdentifier"], "retrieved": document["retrieved_at"]}).scalar_one()
            ballot_row = connection.execute(text("SELECT official_document_id,status FROM ballot_versions WHERE id=:id"), {"id": ballot_id}).mappings().one()
            if ballot_row["official_document_id"] != document_id or ballot_row["status"] != "draft":
                raise ValueError("existing ballot version is not the same editable draft")
            counts["ballotVersions"] += 1
            for item in ballot["items"]:
                race_id = race_ids.get(item["key"]) if item["type"] == "race" else None
                proposition_id = proposition_ids.get(item["key"]) if item["type"] == "proposition" else None
                connection.execute(text(
                    "INSERT INTO ballot_items (id,publication_id,ballot_version_id,race_id,proposition_id,sequence,source_page) "
                    "VALUES (gen_random_uuid(),:p,:b,:r,:q,:s,:page) ON CONFLICT ON CONSTRAINT uq_ballot_items_version_sequence DO NOTHING"
                ), {"p": publication_id, "b": ballot_id, "r": race_id, "q": proposition_id, "s": item["sequence"], "page": item["sourcePage"]})
                stored_item = connection.execute(text("SELECT race_id,proposition_id,source_page FROM ballot_items WHERE ballot_version_id=:b AND sequence=:s"), {"b": ballot_id, "s": item["sequence"]}).mappings().one()
                _same(stored_item, {"race_id": race_id, "proposition_id": proposition_id, "source_page": item["sourcePage"]}, "ballot item")
                counts["items"] += 1
            item_count = connection.execute(text("SELECT COUNT(*) FROM ballot_items WHERE ballot_version_id=:b"), {"b": ballot_id}).scalar_one()
            if item_count != len(ballot["items"]):
                raise ValueError("existing ballot version has items outside the pinned manifest")
            for requirement in ballot["geographicRequirements"]:
                area = connection.execute(text(
                    "SELECT ga.id,ga.authority_id FROM geographic_areas ga JOIN election_authorities ea ON ea.id=ga.authority_id "
                    "WHERE ea.publication_id=:p AND ea.slug=:authority AND ga.slug=:area AND ga.status='active'"
                ), {"p": publication_id, "authority": requirement["authoritySlug"], "area": requirement["areaSlug"]}).mappings().one_or_none()
                if area is None:
                    raise ValueError("a required active geographic area was not found")
                connection.execute(text(
                    "INSERT INTO ballot_geographic_requirements (ballot_version_id,publication_id,geographic_area_id,authority_id,source_document_id,verified_by_reference,verified_at) "
                    "VALUES (:b,:p,:area,:authority,:doc,:reviewer,CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING"
                ), {"b": ballot_id, "p": publication_id, "area": area["id"], "authority": area["authority_id"], "doc": document_id, "reviewer": requirement["verifiedByReference"]})
                stored_requirement = connection.execute(text(
                    "SELECT source_document_id,verified_by_reference FROM ballot_geographic_requirements "
                    "WHERE ballot_version_id=:b AND geographic_area_id=:area"
                ), {"b": ballot_id, "area": area["id"]}).mappings().one()
                _same(stored_requirement, {"source_document_id": document_id,
                    "verified_by_reference": requirement["verifiedByReference"]}, "geographic requirement")
            requirement_count = connection.execute(text(
                "SELECT COUNT(*) FROM ballot_geographic_requirements WHERE ballot_version_id=:b"
            ), {"b": ballot_id}).scalar_one()
            if requirement_count != len(ballot["geographicRequirements"]):
                raise ValueError("existing ballot version has geographic requirements outside the pinned manifest")
    return counts


def summary(manifest: dict[str, Any]) -> str:
    candidates = sum(len(race["candidates"]) for race in manifest["races"])
    items = sum(len(ballot["items"]) for ballot in manifest["ballotVersions"])
    return f"Validated {len(manifest['ballotVersions'])} ballot version(s), {len(manifest['races'])} race(s), {candidates} candidate(s), {len(manifest.get('propositions', []))} proposition(s), and {items} item(s)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate or import a pinned official ballot manifest as draft data.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    manifest = read_manifest(arguments.manifest)
    print(summary(manifest))
    if arguments.apply:
        counts = apply_manifest(manifest)
        print(f"Imported draft official ballot data: {counts}")
    else:
        print("Dry run only; no database writes were made")


if __name__ == "__main__":
    main()
