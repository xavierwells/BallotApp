from pathlib import Path

import pytest

from app.cli.import_browse_coverage import read_manifest


def pilot_manifest() -> Path | None:
    return next(
        (
            parent / "data" / "browse" / "copperas-cove-pilot.json"
            for parent in Path(__file__).resolve().parents
            if (parent / "data" / "browse" / "copperas-cove-pilot.json").is_file()
        ),
        None,
    )


def test_pilot_manifest_pins_the_reviewed_population_calculation() -> None:
    path = pilot_manifest()
    if path is None:
        pytest.skip("browse manifest is validated from the repository checkout in CI")
    manifest = read_manifest(path)

    assert manifest["zcta"]["query"] == "76522"
    assert manifest["population"]["expectedBlockCount"] == 711
    assert manifest["population"]["expectedTotalPopulation"] == 41123
    assert [(target["countyFips"], target["expectedPopulation"]) for target in manifest["targets"]] == [
        ("099", 38975),
        ("281", 2148),
    ]
    assert manifest["methodologyVersion"] == "census-zcta-contained-block-pop100-v1"
    assert manifest["sourceReview"]["permittedUse"] == "private_retention"
    assert manifest["sourceReview"]["costModel"] == "free"
