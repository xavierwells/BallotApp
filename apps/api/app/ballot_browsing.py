"""Coarse ballot discovery that never claims an exact voter match."""

from __future__ import annotations

from datetime import UTC, date, datetime
import os
from typing import Protocol
from uuid import UUID

from app.schemas.ballot_resolution import (
    BallotBrowseResponse,
    BallotChoice,
    BrowseAreaType,
    BrowseBallotMatch,
    GeographicSupport,
    SourceCitation,
)


class BallotBrowser(Protocol):
    def browse(self, area_type: BrowseAreaType, query: str) -> BallotBrowseResponse: ...


class UnavailableBallotBrowser:
    def browse(self, area_type: BrowseAreaType, query: str) -> BallotBrowseResponse:
        return BallotBrowseResponse(
            status="not_available",
            area_type=area_type,
            query=query,
            message="Ballot browsing is not connected yet. No exact voter match was attempted.",
        )


class SyntheticDemoBallotBrowser:
    """Invented development fixture for reviewing coarse browse presentation."""

    def browse(self, area_type: BrowseAreaType, query: str) -> BallotBrowseResponse:
        source = SourceCitation(
            authority_name="Synthetic demo authority — not official",
            source_url="https://example.test/ballotapp-synthetic-demo",
            checked_at=datetime(2026, 8, 20, tzinfo=UTC),
            source_label="Invented source used only for interface review",
        )
        area_label = {
            BrowseAreaType.ZIP: f"Synthetic ZIP area {query}",
            BrowseAreaType.CITY: f"Synthetic city area matching {query}",
            BrowseAreaType.COUNTY: f"Synthetic county area matching {query}",
        }[area_type]
        matches: list[BrowseBallotMatch] = []
        for index in (1, 2):
            support = GeographicSupport(
                geographic_area_id=UUID(f"00000000-0000-0000-0000-{index + 30:012d}"),
                area_type=area_type.value,
                name=area_label,
                boundary_version_id=UUID(f"10000000-0000-0000-0000-{index + 30:012d}"),
                explanation=(
                    f"This invented ballot overlaps the selected {area_type.value} area. "
                    "An address-level match was not attempted."
                ),
                source=source,
            )
            matches.append(
                BrowseBallotMatch(
                    ballot=BallotChoice(
                        ballot_version_id=UUID(f"00000000-0000-0000-0000-{index + 200:012d}"),
                        label=f"DEMO — Ballot available in part of this area {index}",
                        election_name="Synthetic November 2026 Election",
                        election_date=date(2026, 11, 3),
                        official_source=source,
                    ),
                    geographic_support=[support],
                    relationship="overlaps",
                    rank=index,
                    estimated_area_share_percent=95 if index == 1 else 5,
                    coverage_basis="residential_population_estimate",
                    coverage_source=source,
                    most_common_area_match=index == 1,
                    explanation=(
                        f"This is one of multiple invented ballots found within the selected {area_type.value}. "
                        "Choose it only to browse its contents, not as an exact voter match."
                    ),
                )
            )
        return BallotBrowseResponse(
            status="available",
            area_type=area_type,
            query=query,
            demonstration=True,
            message=(
                f"Two synthetic ballots overlap the selected {area_type.value}. "
                "Browsing does not determine which ballot applies to a voter."
            ),
            matches=matches,
        )


def browser_from_environment() -> BallotBrowser:
    demo_enabled = os.getenv("BALLOT_RESOLUTION_DEMO_ENABLED", "false").strip().lower() == "true"
    if demo_enabled and os.getenv("APP_ENV", "development").strip().lower() == "development":
        return SyntheticDemoBallotBrowser()
    return UnavailableBallotBrowser()
