import json
from pathlib import Path

import pytest

from app.cli.import_boundary_manifest import arguments_for, read_manifest


def repository_manifest() -> Path | None:
    return next(
        (
            parent / "data" / "boundaries" / "copperas-cove-2026-primary-reference.json"
            for parent in Path(__file__).resolve().parents
            if (parent / "data" / "boundaries" / "copperas-cove-2026-primary-reference.json").is_file()
        ),
        None,
    )


def test_pilot_boundary_manifest_is_pinned_and_reference_only() -> None:
    path = repository_manifest()
    if path is None:
        pytest.skip("boundary manifest is validated from the repository checkout in CI")
    manifest = read_manifest(path)

    assert manifest["resolutionEligibility"] == "reference_only"
    assert manifest["sourceSrid"] == 3081
    assert manifest["sha256"] == "70a67743d55a218ba5ce6057816563376f61cf0bc531a77d1edc98644c310107"
    assert {item["subjectSlug"] for item in manifest["imports"]} == {
        "bell-county", "coryell-county", "lampasas-county"
    }
    assert sum(item["expectedFeatureCount"] for item in manifest["imports"]) == 98


def test_manifest_rejects_non_reference_geometry(tmp_path: Path) -> None:
    path = repository_manifest()
    if path is None:
        pytest.skip("boundary manifest is validated from the repository checkout in CI")
    content = json.loads(path.read_text(encoding="utf-8"))
    content["resolutionEligibility"] = "verified"
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(content), encoding="utf-8")

    with pytest.raises(ValueError, match="reference_only"):
        read_manifest(invalid)


def test_manifest_arguments_never_promote_reference_geometry() -> None:
    path = repository_manifest()
    if path is None:
        pytest.skip("boundary manifest is validated from the repository checkout in CI")
    manifest = read_manifest(path)
    arguments = arguments_for(manifest, manifest["imports"][0], apply=True)

    assert arguments.subject_slug == "bell-county"
    assert arguments.filter_field == "CNTY"
    assert arguments.filter_value == "27"
