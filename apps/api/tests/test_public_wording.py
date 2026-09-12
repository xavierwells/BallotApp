from app.resolution_pipeline import ResolutionPipeline, SyntheticDemoResolutionPipeline
from app.geocoding import DisabledGeocoder


def test_unconfigured_lookup_explains_gap_without_reflecting_address():
    result = ResolutionPipeline(context=None, geocoder=DisabledGeocoder()).resolve("Private test address only")
    assert "haven't connected an election" in result.message
    assert "not saved" in result.message
    assert "Private test address" not in result.model_dump_json()
    assert result.address_persisted is False


def test_demo_explanations_are_plain_and_explicitly_invented():
    result = SyntheticDemoResolutionPipeline("resolved").resolve("Synthetic test input")
    assert result.demonstration is True
    for item in result.supported_by:
        assert "invented example" in item.explanation
        assert "not real election information" in item.explanation
        assert item.source.source_url
