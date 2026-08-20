from pathlib import Path

from app.cli.import_browse_coverage import read_manifest


def pilot_manifest() -> Path:
    path = next(
        (
            parent / "data" / "browse" / "copperas-cove-pilot.json"
            for parent in Path(__file__).resolve().parents
            if (parent / "data" / "browse" / "copperas-cove-pilot.json").is_file()
        ),
        None,
    )
    assert path is not None, "required browse manifest is missing; mount repository data/ at /app/data"
    return path


def test_pilot_manifest_pins_the_reviewed_population_calculation() -> None:
    path = pilot_manifest()
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
