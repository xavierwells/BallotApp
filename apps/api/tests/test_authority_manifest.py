from pathlib import Path

from app.cli.bootstrap_authorities import read_manifest


def test_copperas_cove_manifest_has_the_required_pilot_authorities() -> None:
    manifest_path = Path(__file__).resolve().parents[3] / "data" / "authorities" / "copperas-cove-pilot.json"

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
