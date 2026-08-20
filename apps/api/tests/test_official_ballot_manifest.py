import json
from pathlib import Path

import pytest

from app.cli.import_official_ballot import read_manifest, summary


def fixture_path() -> Path:
    path = next(
        (parent / "data" / "ballots" / "synthetic-official-ballot.json" for parent in Path(__file__).resolve().parents
         if (parent / "data" / "ballots" / "synthetic-official-ballot.json").is_file()),
        None,
    )
    assert path is not None, "required synthetic ballot manifest is missing; mount repository data/ at /app/data"
    return path


def test_synthetic_official_ballot_manifest_is_complete_and_dry_run_safe() -> None:
    manifest = read_manifest(fixture_path())
    assert manifest["ballotVersions"][0]["externalIdentifier"] == "synthetic-style-001"
    assert summary(manifest) == (
        "Validated 1 ballot version(s), 1 race(s), 2 candidate(s), 1 proposition(s), and 2 item(s)"
    )


def test_manifest_rejects_unknown_item_reference(tmp_path: Path) -> None:
    content = json.loads(fixture_path().read_text(encoding="utf-8"))
    content["ballotVersions"][0]["items"][0]["key"] = "missing-race"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown race"):
        read_manifest(path)


def test_manifest_rejects_missing_page_citation(tmp_path: Path) -> None:
    content = json.loads(fixture_path().read_text(encoding="utf-8"))
    del content["ballotVersions"][0]["items"][0]["sourcePage"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(ValueError, match="sourcePage"):
        read_manifest(path)


def test_manifest_rejects_unverified_geographic_requirement(tmp_path: Path) -> None:
    content = json.loads(fixture_path().read_text(encoding="utf-8"))
    del content["ballotVersions"][0]["geographicRequirements"][0]["verifiedByReference"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(ValueError, match="verifiedByReference"):
        read_manifest(path)
