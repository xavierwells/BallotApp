from pathlib import Path

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
    assert manifest_path is not None, "required pilot authority manifest is missing; mount repository data/ at /app/data"

    manifest = read_manifest(manifest_path)

    authority_slugs = {authority["slug"] for authority in manifest["authorities"]}
    assert {
        "city-of-copperas-cove",
        "coryell-county",
        "bell-county",
        "lampasas-county",
        "copperas-cove-isd",
        "texas-secretary-of-state-elections",
        "texas-legislative-council",
        "us-census-bureau",
    } <= authority_slugs
    assert all(
        source.get("approvalStatus", "pending_review") == "pending_review"
        for authority in manifest["authorities"]
        for source in authority["sources"]
    )
    tlc = next(authority for authority in manifest["authorities"] if authority["slug"] == "texas-legislative-council")
    assert tlc["sources"][0]["monitoringClass"] == "reference"
    assert all(
        source["permittedUse"] == "direct_link_manual_check"
        for authority in manifest["authorities"]
        for source in authority["sources"]
    )
