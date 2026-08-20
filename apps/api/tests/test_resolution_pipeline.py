from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.ballot_matching import BallotMatch, BallotMatchStatus
from app.boundary_resolution import BoundaryMembership, BoundaryResolution, BoundaryResolutionStatus
from app.geocoding import GeocodeResult, GeocodeStatus
from app.resolution_pipeline import ResolutionContext, ResolutionPipeline, pipeline_from_environment
from app.schemas.ballot_resolution import BallotChoice, SourceCitation


SYNTHETIC_ADDRESS = "914 Example Street, Copperas Cove, TX 76522"
PUBLICATION_ID = UUID("00000000-0000-0000-0000-000000000001")
ELECTION_ID = UUID("00000000-0000-0000-0000-000000000002")
AREA_1 = UUID("00000000-0000-0000-0000-000000000010")
AREA_2 = UUID("00000000-0000-0000-0000-000000000011")
BALLOT_1 = UUID("00000000-0000-0000-0000-000000000100")
BALLOT_2 = UUID("00000000-0000-0000-0000-000000000101")


class FakeGeocoder:
    def __init__(self, status: GeocodeStatus = GeocodeStatus.MATCHED) -> None:
        self.status = status

    def geocode(self, address: str) -> GeocodeResult:
        assert address == SYNTHETIC_ADDRESS
        if self.status is GeocodeStatus.MATCHED:
            return GeocodeResult(status=self.status, longitude=-97.9, latitude=31.1)
        return GeocodeResult(status=self.status)


class FakeBoundaryResolver:
    def __init__(self, result: BoundaryResolution) -> None:
        self.result = result

    def resolve(self, **_arguments: object) -> BoundaryResolution:
        return self.result


class FakeBallotMatcher:
    def __init__(self, result: BallotMatch) -> None:
        self.result = result

    def match(self, **_arguments: object) -> BallotMatch:
        return self.result


class FakeCatalog:
    def __init__(self, ballot_ids: tuple[UUID, ...]) -> None:
        self.ballot_ids = ballot_ids

    def choices(self, ballot_version_ids: tuple[UUID, ...]) -> dict[UUID, BallotChoice]:
        assert ballot_version_ids == self.ballot_ids
        return {
            ballot_id: BallotChoice(
                ballot_version_id=ballot_id,
                label=f"Synthetic ballot {index}",
                election_name="Synthetic General Election",
                election_date=date(2026, 11, 3),
                official_source=SourceCitation(
                    authority_name="Synthetic Authority",
                    source_url="https://example.test/official-ballot",
                    checked_at=datetime(2026, 8, 20, tzinfo=UTC),
                    source_label="Synthetic official ballot",
                ),
            )
            for index, ballot_id in enumerate(ballot_version_ids, start=1)
        }

    def required_area_ids(self, ballot_version_ids: tuple[UUID, ...]) -> dict[UUID, frozenset[UUID]]:
        return {
            ballot_id: frozenset({AREA_1 if ballot_id == BALLOT_1 else AREA_2})
            for ballot_id in ballot_version_ids
        }


def membership(area_id: UUID, number: int) -> BoundaryMembership:
    return BoundaryMembership(
        boundary_version_id=UUID(f"10000000-0000-0000-0000-{number:012d}"),
        geographic_area_id=area_id,
        authority_id=UUID(f"20000000-0000-0000-0000-{number:012d}"),
        area_type="voting_precinct",
        area_name=f"Synthetic Precinct {number}",
        authority_name="Synthetic Authority",
        source_url="https://example.test/synthetic-boundaries",
        source_checked_at=datetime(2026, 8, 20, tzinfo=UTC),
        source_label="Synthetic boundary dataset",
        on_boundary_edge=False,
    )


def pipeline(boundary: BoundaryResolution, ballot_match: BallotMatch, ballot_ids: tuple[UUID, ...]) -> ResolutionPipeline:
    return ResolutionPipeline(
        context=ResolutionContext(PUBLICATION_ID, ELECTION_ID, date(2026, 11, 3)),
        geocoder=FakeGeocoder(),
        boundary_resolver=FakeBoundaryResolver(boundary),  # type: ignore[arg-type]
        ballot_matcher=FakeBallotMatcher(ballot_match),  # type: ignore[arg-type]
        ballot_catalog=FakeCatalog(ballot_ids),
    )


def test_exact_pipeline_returns_one_evidenced_ballot_without_request_data() -> None:
    result = pipeline(
        BoundaryResolution(BoundaryResolutionStatus.MATCHED, (membership(AREA_1, 1),), ()),
        BallotMatch(BallotMatchStatus.MATCHED, (BALLOT_1,)),
        (BALLOT_1,),
    ).resolve(SYNTHETIC_ADDRESS)

    assert result.status == "resolved"
    assert result.address_persisted is False
    assert result.supported_by[0].geographic_area_id == AREA_1  # type: ignore[attr-defined]
    assert SYNTHETIC_ADDRESS not in repr(result)
    assert "-97.9" not in repr(result)


def test_ambiguous_pipeline_returns_two_ballots_without_preselection() -> None:
    result = pipeline(
        BoundaryResolution(
            BoundaryResolutionStatus.AMBIGUOUS,
            (membership(AREA_1, 1), membership(AREA_2, 2)),
            (),
        ),
        BallotMatch(BallotMatchStatus.MULTIPLE_MATCHES, (BALLOT_1, BALLOT_2)),
        (BALLOT_1, BALLOT_2),
    ).resolve(SYNTHETIC_ADDRESS)

    assert result.status == "ambiguous"
    assert len(result.plausible_ballots) == 2  # type: ignore[attr-defined]
    assert result.plausible_ballots[0].supported_by[0].geographic_area_id == AREA_1  # type: ignore[attr-defined]
    assert result.plausible_ballots[1].supported_by[0].geographic_area_id == AREA_2  # type: ignore[attr-defined]


def test_unmatched_geocode_returns_without_spatial_request_data() -> None:
    result = ResolutionPipeline(
        context=ResolutionContext(PUBLICATION_ID, ELECTION_ID, date(2026, 11, 3)),
        geocoder=FakeGeocoder(GeocodeStatus.UNMATCHED),
        boundary_resolver=FakeBoundaryResolver(BoundaryResolution(BoundaryResolutionStatus.NOT_FOUND, (), ())),  # type: ignore[arg-type]
        ballot_matcher=FakeBallotMatcher(BallotMatch(BallotMatchStatus.NOT_FOUND, ())),  # type: ignore[arg-type]
        ballot_catalog=FakeCatalog(()),
    ).resolve(SYNTHETIC_ADDRESS)

    assert result.status == "not_found"
    assert result.address_persisted is False
    assert SYNTHETIC_ADDRESS not in repr(result)


def test_invalid_election_configuration_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BALLOT_RESOLUTION_PUBLICATION_ID", "not-a-uuid")
    monkeypatch.setenv("BALLOT_RESOLUTION_ELECTION_ID", str(ELECTION_ID))
    monkeypatch.setenv("BALLOT_RESOLUTION_ELECTION_DATE", "2026-11-03")
    monkeypatch.setenv("GEOCODER_PROVIDER", "disabled")

    result = pipeline_from_environment().resolve(SYNTHETIC_ADDRESS)
    assert result.status == "not_available"
    assert SYNTHETIC_ADDRESS not in repr(result)
