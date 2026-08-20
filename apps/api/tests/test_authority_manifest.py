from pathlib import Path

import pytest

from app.cli.bootstrap_authorities import read_manifest


def test_copperas_cove_manifest_has_the_required_pilot_authorities() -> None:
    manifest_path = next(
        (
            parent / "data" / "authorities" / "copperas-cove-pilot.json"
            for parent in Path(__file__).resolve().parents
            if (parent / "data" / "authorities" / "copperas-cove-pilot.json").is_file()
        ),
        None,
    )
    if manifest_path is None:
        pytest.skip("pilot manifest is mounted at runtime and is validated from the repository checkout in CI")

    manifest = read_manifest(manifest_path)

    authority_slugs = {authority["slug"] for authority in manifest["authorities"]}
    assert {
        "city-of-copperas-cove",
        "coryell-county",
        "bell-county",
        "lampasas-county",
        "copperas-cove-isd",
        "texas-secretary-of-state-elections",
    } <= authority_slugs
    assert all(
        source.get("approvalStatus", "pending_review") == "pending_review"
        for authority in manifest["authorities"]
        for source in authority["sources"]
    )
    assert all(
        source["monitoringClass"] == "active_election"
        for authority in manifest["authorities"]
        for source in authority["sources"]
    )
