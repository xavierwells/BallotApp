"""Coarse ballot discovery that never claims an exact voter match."""

from __future__ import annotations

from datetime import UTC, date, datetime
import os
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.database import get_engine
from app.schemas.ballot_resolution import (
    BallotBrowseResponse,
    BallotChoice,
    BrowseAreaType,
    BrowseBallotMatch,
    BrowseGeographicMatch,
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
                    coverage_sources=[source],
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


class PostgresBallotBrowser:
    """Read only reviewed coarse-area estimates; ballot lookup remains separate."""

    def __init__(self, engine: Engine, organization_slug: str, publication_slug: str) -> None:
        self.engine = engine
        self.organization_slug = organization_slug
        self.publication_slug = publication_slug

    def browse(self, area_type: BrowseAreaType, query: str) -> BallotBrowseResponse:
        if area_type is not BrowseAreaType.ZIP:
            return BallotBrowseResponse(
                status="not_available",
                area_type=area_type,
                query=query,
                message=f"Reviewed {area_type.value} browse coverage is not connected yet.",
            )
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT ba.source_vintage, e.id AS estimate_id, e.rank, e.estimated_share_percent, "
                    "e.coverage_basis, ga.id AS geographic_area_id, ga.name, ga.area_type, "
                    "d.id AS document_id, d.title, d.publisher_name, d.source_url, d.retrieved_at "
                    "FROM organizations o JOIN publications p ON p.organization_id = o.id "
                    "JOIN browse_areas ba ON ba.publication_id = p.id "
                    "JOIN browse_coverage_estimates e ON e.browse_area_id = ba.id "
                    "JOIN geographic_areas ga ON ga.id = e.target_geographic_area_id "
                    "JOIN browse_coverage_evidence ev ON ev.coverage_estimate_id = e.id "
                    "JOIN documents d ON d.id = ev.source_document_id "
                    "WHERE o.slug = :organization_slug AND p.slug = :publication_slug "
                    "AND ba.area_type = 'zip' AND ba.query_key = :query "
                    "AND ba.status = 'verified' AND e.status = 'verified' AND ga.status = 'active' "
                    "AND e.target_kind = 'geographic_area' ORDER BY e.rank, d.id"
                ),
                {
                    "query": query,
                    "organization_slug": self.organization_slug,
                    "publication_slug": self.publication_slug,
                },
            ).mappings().all()
        if not rows:
            return BallotBrowseResponse(
                status="not_found",
                area_type=area_type,
                query=query,
                message="No reviewed Census ZIP-area coverage was found. No exact voter match was attempted.",
            )

        grouped: dict[UUID, dict[str, object]] = {}
        for row in rows:
            estimate = grouped.setdefault(row["estimate_id"], {"row": row, "citations": []})
            citations = estimate["citations"]
            assert isinstance(citations, list)
            citations.append(
                SourceCitation(
                    authority_name=row["publisher_name"],
                    source_url=row["source_url"],
                    checked_at=row["retrieved_at"],
                    source_label=row["title"],
                )
            )
        area_matches: list[BrowseGeographicMatch] = []
        for estimate in sorted(grouped.values(), key=lambda item: item["row"]["rank"]):  # type: ignore[index]
            row = estimate["row"]
            citations = estimate["citations"]
            area_matches.append(
                BrowseGeographicMatch(
                    geographic_area_id=row["geographic_area_id"],  # type: ignore[index]
                    name=row["name"],  # type: ignore[index]
                    area_type=row["area_type"],  # type: ignore[index]
                    rank=row["rank"],  # type: ignore[index]
                    estimated_area_share_percent=float(row["estimated_share_percent"]),  # type: ignore[index]
                    coverage_basis=row["coverage_basis"],  # type: ignore[index]
                    coverage_sources=citations,  # type: ignore[arg-type]
                    most_common_area_match=row["rank"] == 1,  # type: ignore[index]
                    explanation=(
                        f"Estimated from {row['source_vintage']} aggregate population. "  # type: ignore[index]
                        "This area ranking does not identify a voter's county, precinct, or ballot."
                    ),
                )
            )
        return BallotBrowseResponse(
            status="available",
            area_type=area_type,
            query=query,
            message=(
                "Reviewed geographic area estimates are available. Official ballot versions are not connected, "
                "so no ballot has been selected."
            ),
            area_matches=area_matches,
        )


def browser_from_environment() -> BallotBrowser:
    database_enabled = os.getenv("BALLOT_BROWSE_DATABASE_ENABLED", "false").strip().lower() == "true"
    if database_enabled:
        return PostgresBallotBrowser(
            get_engine(),
            os.getenv("BALLOT_BROWSE_ORGANIZATION_SLUG", "whats-on-my-ballot").strip(),
            os.getenv("BALLOT_BROWSE_PUBLICATION_SLUG", "copperas-cove").strip(),
        )
    demo_enabled = os.getenv("BALLOT_RESOLUTION_DEMO_ENABLED", "false").strip().lower() == "true"
    if demo_enabled and os.getenv("APP_ENV", "development").strip().lower() == "development":
        return SyntheticDemoBallotBrowser()
    return UnavailableBallotBrowser()
