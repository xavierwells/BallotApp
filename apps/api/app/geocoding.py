"""Ephemeral geocoder adapters.

No type in this module contains an address after ``geocode`` returns. Provider
requests are single-attempt and uncached; callers must not log their input.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import os
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CENSUS_GEOCODER_ENDPOINT = (
    "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
)
MAX_PROVIDER_RESPONSE_BYTES = 1_000_000


class GeocoderError(RuntimeError):
    """Provider failure that is safe to surface without request data."""


class GeocodeStatus(StrEnum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"
    NOT_AVAILABLE = "not_available"


@dataclass(frozen=True)
class GeocodeResult:
    """Request-scoped coordinates and non-identifying provider metadata."""

    status: GeocodeStatus
    longitude: float | None = None
    latitude: float | None = None
    provider: str | None = None
    benchmark: str | None = None


class Geocoder(Protocol):
    def geocode(self, address: str) -> GeocodeResult: ...


class DisabledGeocoder:
    def geocode(self, address: str) -> GeocodeResult:
        del address
        return GeocodeResult(status=GeocodeStatus.NOT_AVAILABLE)


class CensusGeocoder:
    """Server-side adapter for the U.S. Census single-address geocoder."""

    def __init__(self, *, timeout_seconds: float = 5.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("geocoder timeout must be positive")
        self.timeout_seconds = timeout_seconds

    def geocode(self, address: str) -> GeocodeResult:
        if not 5 <= len(address) <= 300:
            raise ValueError("address length is outside the accepted request range")

        query = urlencode(
            {
                "address": address,
                "benchmark": "Public_AR_Current",
                "format": "json",
            }
        )
        request = Request(
            f"{CENSUS_GEOCODER_ENDPOINT}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "BallotApp/0.2 (ephemeral address resolution)",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise GeocoderError("the geocoder provider is unavailable") from error

        if len(payload) > MAX_PROVIDER_RESPONSE_BYTES:
            raise GeocoderError("the geocoder provider response exceeded the safety limit")
        try:
            result = json.loads(payload)["result"]
            matches = result["addressMatches"]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise GeocoderError("the geocoder provider returned an invalid response") from error
        if not isinstance(matches, list):
            raise GeocoderError("the geocoder provider returned an invalid match list")

        benchmark = self._benchmark_name(result)
        if not matches:
            return GeocodeResult(
                status=GeocodeStatus.UNMATCHED,
                provider="us_census",
                benchmark=benchmark,
            )
        if len(matches) != 1:
            return GeocodeResult(
                status=GeocodeStatus.AMBIGUOUS,
                provider="us_census",
                benchmark=benchmark,
            )

        try:
            longitude = float(matches[0]["coordinates"]["x"])
            latitude = float(matches[0]["coordinates"]["y"])
        except (KeyError, TypeError, ValueError) as error:
            raise GeocoderError("the geocoder provider returned invalid coordinates") from error
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise GeocoderError("the geocoder provider returned out-of-range coordinates")
        return GeocodeResult(
            status=GeocodeStatus.MATCHED,
            longitude=longitude,
            latitude=latitude,
            provider="us_census",
            benchmark=benchmark,
        )

    @staticmethod
    def _benchmark_name(result: object) -> str | None:
        if not isinstance(result, dict):
            return None
        provider_input = result.get("input")
        if not isinstance(provider_input, dict):
            return None
        benchmark = provider_input.get("benchmark")
        if not isinstance(benchmark, dict):
            return None
        name = benchmark.get("benchmarkName")
        return name if isinstance(name, str) else None


def geocoder_from_environment() -> Geocoder:
    """Return the explicitly configured adapter; external calls default off."""
    provider = os.getenv("GEOCODER_PROVIDER", "disabled").strip().lower()
    if provider == "disabled":
        return DisabledGeocoder()
    if provider == "census":
        timeout = float(os.getenv("GEOCODER_TIMEOUT_SECONDS", "5"))
        return CensusGeocoder(timeout_seconds=timeout)
    raise RuntimeError("GEOCODER_PROVIDER must be 'disabled' or 'census'")
