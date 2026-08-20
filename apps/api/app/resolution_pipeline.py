"""Request-scoped address-to-ballot orchestration with no voter-data retention."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import os
from typing import Protocol
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from app.ballot_matching import BallotMatcher, BallotMatchStatus, PostgresBallotRequirementRepository
from app.boundary_resolution import (
    BoundaryMembership,
    BoundaryResolutionStatus,
    BoundaryResolver,
    PostgisBoundaryRepository,
)
from app.database import get_engine
from app.geocoding import Geocoder, GeocoderError, GeocodeStatus, geocoder_from_environment
from app.schemas.ballot_resolution import (
    BallotChoice,
    BallotResolutionResponse,
    GeographicSupport,
    MultipleBallotsResponse,
    NeedsReviewResponse,
    NotAvailableResponse,
    NotFoundResponse,
    PlausibleBallot,
    ResolvedBallotResponse,
    SourceCitation,
)


@dataclass(frozen=True)
class ResolutionContext:
    publication_id: UUID
    election_id: UUID
    election_date: date


class BallotCatalog(Protocol):
    def choices(self, ballot_version_ids: tuple[UUID, ...]) -> dict[UUID, BallotChoice]: ...

    def required_area_ids(self, ballot_version_ids: tuple[UUID, ...]) -> dict[UUID, frozenset[UUID]]: ...


class PostgresBallotCatalog:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def choices(self, ballot_version_ids: tuple[UUID, ...]) -> dict[UUID, BallotChoice]:
        if not ballot_version_ids:
            return {}
        statement = text(
            "SELECT bv.id, COALESCE(bv.external_identifier, e.jurisdiction_name) AS label, "
            "e.jurisdiction_name || ' ' || e.election_type AS election_name, e.election_date, "
            "e.authority_name, d.source_url, d.retrieved_at AS checked_at, d.title AS source_label "
            "FROM ballot_versions bv JOIN elections e ON e.id = bv.election_id "
            "JOIN documents d ON d.id = bv.official_document_id "
            "WHERE bv.id IN :ballot_ids AND bv.status = 'published'"
        ).bindparams(bindparam("ballot_ids", expanding=True))
        with self.engine.connect() as connection:
            rows = connection.execute(statement, {"ballot_ids": ballot_version_ids}).mappings()
            return {
                row["id"]: BallotChoice(
                    ballot_version_id=row["id"],
                    label=row["label"],
                    election_name=row["election_name"],
                    election_date=row["election_date"],
                    official_source=SourceCitation(
                        authority_name=row["authority_name"],
                        source_url=row["source_url"],
                        checked_at=row["checked_at"],
                        source_label=row["source_label"],
                    ),
                )
                for row in rows
            }

    def required_area_ids(self, ballot_version_ids: tuple[UUID, ...]) -> dict[UUID, frozenset[UUID]]:
        if not ballot_version_ids:
            return {}
        statement = text(
            "SELECT ballot_version_id, geographic_area_id FROM ballot_geographic_requirements "
            "WHERE ballot_version_id IN :ballot_ids ORDER BY ballot_version_id, geographic_area_id"
        ).bindparams(bindparam("ballot_ids", expanding=True))
        grouped: dict[UUID, set[UUID]] = {ballot_id: set() for ballot_id in ballot_version_ids}
        with self.engine.connect() as connection:
            for row in connection.execute(statement, {"ballot_ids": ballot_version_ids}):
                grouped[row[0]].add(row[1])
        return {ballot_id: frozenset(area_ids) for ballot_id, area_ids in grouped.items()}


class ResolutionPipeline:
    def __init__(
        self,
        *,
        context: ResolutionContext | None,
        geocoder: Geocoder,
        boundary_resolver: BoundaryResolver | None = None,
        ballot_matcher: BallotMatcher | None = None,
        ballot_catalog: BallotCatalog | None = None,
    ) -> None:
        self.context = context
        self.geocoder = geocoder
        self.boundary_resolver = boundary_resolver
        self.ballot_matcher = ballot_matcher
        self.ballot_catalog = ballot_catalog

    def resolve(self, address: str) -> BallotResolutionResponse:
        if self.context is None or not all(
            (self.boundary_resolver, self.ballot_matcher, self.ballot_catalog)
        ):
            del address
            return NotAvailableResponse(
                message="Ballot resolution is not configured for an active election. The submitted address was discarded."
            )
        try:
            geocode = self.geocoder.geocode(address)
        except GeocoderError:
            return NotAvailableResponse(
                message="The address provider is temporarily unavailable. The submitted address was discarded."
            )
        finally:
            del address

        if geocode.status is GeocodeStatus.NOT_AVAILABLE:
            return NotAvailableResponse(
                message="Address resolution is disabled. The submitted address was discarded."
            )
        if geocode.status is GeocodeStatus.UNMATCHED:
            return NotFoundResponse(
                reason_codes=["no_boundary_match"],
                message="The address could not be located. No ballot was selected.",
            )
        if geocode.status is GeocodeStatus.AMBIGUOUS:
            return NeedsReviewResponse(
                confidence=0,
                reason_codes=["low_geocode_confidence"],
                message="The address provider returned multiple locations. No ballot was selected.",
            )
        assert geocode.longitude is not None and geocode.latitude is not None

        return self._resolve_point(longitude=geocode.longitude, latitude=geocode.latitude)

    def resolve_location(
        self, *, longitude: float, latitude: float, accuracy_meters: float
    ) -> BallotResolutionResponse:
        """Resolve a browser-provided location without retaining or echoing it."""
        if self.context is None or not all(
            (self.boundary_resolver, self.ballot_matcher, self.ballot_catalog)
        ):
            return NotAvailableResponse(
                message="Ballot resolution is not configured for an active election. The submitted location was discarded."
            )
        return self._resolve_point(
            longitude=longitude,
            latitude=latitude,
            uncertainty_meters=accuracy_meters,
        )

    def _resolve_point(
        self, *, longitude: float, latitude: float, uncertainty_meters: float = 0
    ) -> BallotResolutionResponse:
        assert self.context is not None
        assert self.boundary_resolver is not None
        assert self.ballot_matcher is not None
        assert self.ballot_catalog is not None

        boundary_result = self.boundary_resolver.resolve(
            longitude=longitude,
            latitude=latitude,
            effective_on=self.context.election_date,
            uncertainty_meters=uncertainty_meters,
        )
        if boundary_result.status is BoundaryResolutionStatus.NOT_FOUND:
            return NotFoundResponse(
                reason_codes=["no_boundary_match"],
                message="No verified boundary covered the resolved location. No ballot was selected.",
            )

        match = self.ballot_matcher.match(
            publication_id=self.context.publication_id,
            election_id=self.context.election_id,
            effective_on=self.context.election_date,
            geographic_area_ids=frozenset(item.geographic_area_id for item in boundary_result.memberships),
        )
        if match.status is BallotMatchStatus.NOT_FOUND:
            return NeedsReviewResponse(
                confidence=0,
                reason_codes=["ballot_data_unavailable"],
                message="The location was resolved, but no published ballot combination matched it.",
            )

        choices = self.ballot_catalog.choices(match.ballot_version_ids)
        if len(choices) != len(match.ballot_version_ids):
            return NotAvailableResponse(message="Published ballot evidence is incomplete. No ballot was selected.")
        required_areas = self.ballot_catalog.required_area_ids(match.ballot_version_ids)
        if any(not required_areas.get(ballot_id) for ballot_id in match.ballot_version_ids):
            return NotAvailableResponse(message="Published ballot geography is incomplete. No ballot was selected.")

        def support_for(ballot_id: UUID) -> list[GeographicSupport]:
            return [
                _support(item)
                for item in boundary_result.memberships
                if item.geographic_area_id in required_areas[ballot_id]
            ]

        if match.status is BallotMatchStatus.MATCHED and boundary_result.status is BoundaryResolutionStatus.MATCHED:
            ballot_id = match.ballot_version_ids[0]
            return ResolvedBallotResponse(
                confidence=100,
                ballot=choices[ballot_id],
                supported_by=support_for(ballot_id),
            )

        plausible = [
            PlausibleBallot(
                ballot=choices[ballot_id],
                supported_by=support_for(ballot_id),
                explanation="This ballot is supported by the listed verified geographic memberships.",
            )
            for ballot_id in match.ballot_version_ids
        ]
        if len(plausible) < 2:
            return NeedsReviewResponse(
                confidence=0,
                reason_codes=[
                    "near_boundary"
                    if boundary_result.status is BoundaryResolutionStatus.AMBIGUOUS
                    else "boundary_source_conflict"
                ],
                message="The geographic evidence is uncertain. No ballot was selected.",
                plausible_ballots=plausible,
            )
        source_conflict = boundary_result.status is BoundaryResolutionStatus.SOURCE_CONFLICT
        return MultipleBallotsResponse(
            status="source_conflict" if source_conflict else "ambiguous",
            confidence=0,
            reason_codes=["boundary_source_conflict" if source_conflict else "near_boundary"],
            message="More than one ballot remains plausible. No ballot was preselected.",
            plausible_ballots=plausible,
        )


class SyntheticDemoResolutionPipeline:
    """Development-only visual fixture; never represents an official ballot."""

    def __init__(self, scenario: str = "resolved") -> None:
        self.scenario = scenario if scenario in {"resolved", "ambiguous", "source_conflict"} else "resolved"

    def resolve(self, address: str) -> BallotResolutionResponse:
        del address
        return self._fixture()

    def resolve_location(
        self, *, longitude: float, latitude: float, accuracy_meters: float
    ) -> BallotResolutionResponse:
        del longitude, latitude, accuracy_meters
        return self._fixture()

    def _fixture(self) -> BallotResolutionResponse:
        checked_at = datetime(2026, 8, 20, tzinfo=UTC)
        source = SourceCitation(
            authority_name="Synthetic demo authority — not official",
            source_url="https://example.test/ballotapp-synthetic-demo",
            checked_at=checked_at,
            source_label="Invented source used only for interface review",
        )
        if self.scenario in {"ambiguous", "source_conflict"}:
            plausible_ballots = []
            for index, area_name in enumerate(("Synthetic Precinct 101", "Synthetic Precinct 102"), start=1):
                support = GeographicSupport(
                    geographic_area_id=UUID(f"00000000-0000-0000-0000-{index + 20:012d}"),
                    area_type="voting_precinct",
                    name=area_name,
                    boundary_version_id=UUID(f"10000000-0000-0000-0000-{index + 20:012d}"),
                    explanation=f"Invented geographic evidence for {area_name}; interface review only.",
                    source=source,
                )
                plausible_ballots.append(
                    PlausibleBallot(
                        ballot=BallotChoice(
                            ballot_version_id=UUID(f"00000000-0000-0000-0000-{index + 100:012d}"),
                            label=f"DEMO — Possible ballot {index}",
                            election_name="Synthetic November 2026 Election",
                            election_date=date(2026, 11, 3),
                            official_source=source,
                        ),
                        supported_by=[support],
                        explanation=(
                            f"This invented ballot is shown because the available evidence supports {area_name}. "
                            "It has not been selected as the voter's ballot."
                        ),
                    )
                )
            source_conflict = self.scenario == "source_conflict"
            return MultipleBallotsResponse(
                status="source_conflict" if source_conflict else "ambiguous",
                demonstration=True,
                confidence=35,
                message=(
                    "Invented official sources disagree, so no exact ballot was selected."
                    if source_conflict
                    else "The invented location is near a precinct boundary, so no exact ballot was selected."
                ),
                reason_codes=["boundary_source_conflict" if source_conflict else "near_boundary"],
                plausible_ballots=plausible_ballots,
            )
        return ResolvedBallotResponse(
            demonstration=True,
            confidence=100,
            ballot=BallotChoice(
                ballot_version_id=UUID("00000000-0000-0000-0000-000000000100"),
                label="DEMO — Synthetic Copperas Cove-style ballot",
                election_name="Synthetic November 2026 Election",
                election_date=date(2026, 11, 3),
                official_source=source,
            ),
            supported_by=[
                GeographicSupport(
                    geographic_area_id=UUID("00000000-0000-0000-0000-000000000010"),
                    area_type="municipality",
                    name="Synthetic City Area",
                    boundary_version_id=UUID("10000000-0000-0000-0000-000000000010"),
                    explanation="Invented point-in-polygon match for interface review only.",
                    source=source,
                ),
                GeographicSupport(
                    geographic_area_id=UUID("00000000-0000-0000-0000-000000000011"),
                    area_type="voting_precinct",
                    name="Synthetic Precinct 101",
                    boundary_version_id=UUID("10000000-0000-0000-0000-000000000011"),
                    explanation="Invented precinct membership for interface review only.",
                    source=source,
                ),
                GeographicSupport(
                    geographic_area_id=UUID("00000000-0000-0000-0000-000000000012"),
                    area_type="school_district",
                    name="Synthetic School District",
                    boundary_version_id=UUID("10000000-0000-0000-0000-000000000012"),
                    explanation="Invented school-district membership for interface review only.",
                    source=source,
                ),
            ],
        )


def _support(membership: BoundaryMembership) -> GeographicSupport:
    return GeographicSupport(
        geographic_area_id=membership.geographic_area_id,
        area_type=membership.area_type,
        name=membership.area_name,
        boundary_version_id=membership.boundary_version_id,
        explanation=f"The resolved point is covered by {membership.area_name}.",
        source=SourceCitation(
            authority_name=membership.authority_name,
            source_url=membership.source_url,
            checked_at=membership.source_checked_at,
            source_label=membership.source_label,
        ),
    )


def pipeline_from_environment() -> ResolutionPipeline | SyntheticDemoResolutionPipeline:
    demo_enabled = os.getenv("BALLOT_RESOLUTION_DEMO_ENABLED", "false").strip().lower() == "true"
    if demo_enabled and os.getenv("APP_ENV", "development").strip().lower() == "development":
        return SyntheticDemoResolutionPipeline(os.getenv("BALLOT_RESOLUTION_DEMO_SCENARIO", "resolved").strip().lower())
    publication = os.getenv("BALLOT_RESOLUTION_PUBLICATION_ID", "").strip()
    election = os.getenv("BALLOT_RESOLUTION_ELECTION_ID", "").strip()
    election_date = os.getenv("BALLOT_RESOLUTION_ELECTION_DATE", "").strip()
    if not all((publication, election, election_date)):
        return ResolutionPipeline(context=None, geocoder=geocoder_from_environment())
    try:
        context = ResolutionContext(UUID(publication), UUID(election), date.fromisoformat(election_date))
    except ValueError:
        return ResolutionPipeline(context=None, geocoder=geocoder_from_environment())
    engine = get_engine()
    return ResolutionPipeline(
        context=context,
        geocoder=geocoder_from_environment(),
        boundary_resolver=BoundaryResolver(PostgisBoundaryRepository(engine)),
        ballot_matcher=BallotMatcher(PostgresBallotRequirementRepository(engine)),
        ballot_catalog=PostgresBallotCatalog(engine),
    )
