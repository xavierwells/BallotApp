import json
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

import app.geocoding as geocoding
from app.geocoding import CensusGeocoder, GeocoderError, GeocodeStatus, geocoder_from_environment


SYNTHETIC_ADDRESS = "914 Example Street, Copperas Cove, TX 76522"


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self.payload


def census_payload(matches: list[dict]) -> dict:
    return {
        "result": {
            "input": {
                "address": {"address": SYNTHETIC_ADDRESS},
                "benchmark": {"benchmarkName": "Public_AR_Current"},
            },
            "addressMatches": matches,
        }
    }


def test_census_adapter_returns_coordinates_without_carrying_the_address(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_open(request: object, *, timeout: float) -> FakeResponse:
        assert parse_qs(urlparse(request.full_url).query)["address"] == [SYNTHETIC_ADDRESS]
        assert timeout == 3
        return FakeResponse(census_payload([{"coordinates": {"x": -97.9, "y": 31.1}}]))

    monkeypatch.setattr(geocoding, "urlopen", fake_open)
    result = CensusGeocoder(timeout_seconds=3).geocode(SYNTHETIC_ADDRESS)

    assert result.status is GeocodeStatus.MATCHED
    assert result.longitude == -97.9
    assert result.latitude == 31.1
    assert result.provider == "us_census"
    assert SYNTHETIC_ADDRESS not in repr(result)


def test_census_adapter_preserves_ambiguous_and_unmatched_states(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = iter(
        [
            census_payload([]),
            census_payload([
                {"coordinates": {"x": -97.9, "y": 31.1}},
                {"coordinates": {"x": -97.8, "y": 31.2}},
            ]),
        ]
    )
    monkeypatch.setattr(geocoding, "urlopen", lambda *_args, **_kwargs: FakeResponse(next(payloads)))
    adapter = CensusGeocoder()

    assert adapter.geocode(SYNTHETIC_ADDRESS).status is GeocodeStatus.UNMATCHED
    ambiguous = adapter.geocode(SYNTHETIC_ADDRESS)
    assert ambiguous.status is GeocodeStatus.AMBIGUOUS
    assert ambiguous.longitude is None
    assert ambiguous.latitude is None


def test_census_adapter_returns_only_safe_provider_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise URLError("synthetic failure")

    monkeypatch.setattr(geocoding, "urlopen", unavailable)
    with pytest.raises(GeocoderError) as captured:
        CensusGeocoder().geocode(SYNTHETIC_ADDRESS)

    assert str(captured.value) == "the geocoder provider is unavailable"
    assert SYNTHETIC_ADDRESS not in str(captured.value)


def test_external_geocoder_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEOCODER_PROVIDER", raising=False)
    result = geocoder_from_environment().geocode(SYNTHETIC_ADDRESS)

    assert result.status is GeocodeStatus.NOT_AVAILABLE
