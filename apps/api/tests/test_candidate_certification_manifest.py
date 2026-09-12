import json
from pathlib import Path

import pytest

from app.cli.stage_candidate_certification import read_manifest, summary


def fixture_path() -> Path:
    path = next(
        (parent / "data" / "candidates" / "texas-2026-general-coryell-certification.json"
         for parent in Path(__file__).resolve().parents
         if (parent / "data" / "candidates" / "texas-2026-general-coryell-certification.json").is_file()),
        None,
    )
    assert path is not None, "required candidate certification manifest is missing; mount repository data/"
    return path


@pytest.mark.parametrize(
    ("county_slug", "county", "race_count", "candidate_count"),
    (
        ("bell", "Bell County", 40, 79),
        ("coryell", "Coryell County", 36, 70),
        ("lampasas", "Lampasas County", 32, 67),
    ),
)
def test_pilot_county_certifications_are_complete(
    county_slug: str, county: str, race_count: int, candidate_count: int
) -> None:
    base = fixture_path().parent
    manifest = read_manifest(base / f"texas-2026-general-{county_slug}-certification.json")
    assert manifest["county"] == county
    assert len(manifest["races"]) == race_count
    assert sum(len(race["candidates"]) for race in manifest["races"]) == candidate_count


def test_real_coryell_certification_is_checksum_pinned_and_staged() -> None:
    manifest = read_manifest(fixture_path())
    assert manifest["status"] == "staged"
    assert manifest["sourceDocument"]["publicAccess"] == "metadata_only"
    assert summary(manifest) == "Validated staged certification for Coryell County: 36 race(s), 70 candidate(s)"
    assert len(manifest["races"]) == 36


def test_certification_rejects_unknown_party(tmp_path: Path) -> None:
    content = json.loads(fixture_path().read_text(encoding="utf-8"))
    content["races"][0]["candidates"][0]["partyLabel"] = "Mystery"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported partyLabel"):
        read_manifest(path)


def test_certification_rejects_missing_page_citation(tmp_path: Path) -> None:
    content = json.loads(fixture_path().read_text(encoding="utf-8"))
    del content["races"][0]["sourcePage"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(ValueError, match="sourcePage"):
        read_manifest(path)
