from datetime import date
from uuid import UUID

import pytest

from app.boundary_resolution import (
    BoundaryMembership,
    BoundaryResolutionReason,
    BoundaryResolutionStatus,
    BoundaryResolver,
)


AUTHORITY_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakeBoundaryRepository:
    def __init__(self, memberships: tuple[BoundaryMembership, ...]) -> None:
        self.memberships = memberships
        self.received: tuple[float, float, date] | None = None

    def memberships_at(
        self, *, longitude: float, latitude: float, effective_on: date
    ) -> tuple[BoundaryMembership, ...]:
        self.received = longitude, latitude, effective_on
        return self.memberships


def membership(number: int, *, area_type: str = "voting_precinct", edge: bool = False) -> BoundaryMembership:
    return BoundaryMembership(
        boundary_version_id=UUID(f"00000000-0000-0000-0000-{number:012d}"),
        geographic_area_id=UUID(f"10000000-0000-0000-0000-{number:012d}"),
        authority_id=AUTHORITY_ID,
        area_type=area_type,
        area_name=f"Synthetic area {number}",
        source_url="https://example.test/synthetic-boundaries",
        on_boundary_edge=edge,
    )


def test_returns_request_scoped_verified_memberships_without_coordinates() -> None:
    repository = FakeBoundaryRepository(
        (membership(1), membership(2, area_type="school_district"))
    )
    result = BoundaryResolver(repository).resolve(
        longitude=-97.90,
        latitude=31.11,
        effective_on=date(2026, 11, 3),
    )

    assert result.status is BoundaryResolutionStatus.MATCHED
    assert result.reasons == ()
    assert repository.received == (-97.90, 31.11, date(2026, 11, 3))
    assert not hasattr(result, "longitude")
    assert not hasattr(result, "latitude")


def test_exact_boundary_edge_is_ambiguous() -> None:
    result = BoundaryResolver(FakeBoundaryRepository((membership(1, edge=True),))).resolve(
        longitude=-97.90,
        latitude=31.11,
        effective_on=date(2026, 11, 3),
    )

    assert result.status is BoundaryResolutionStatus.AMBIGUOUS
    assert result.reasons == (BoundaryResolutionReason.ON_BOUNDARY_EDGE,)


def test_overlapping_interiors_in_one_authority_partition_are_a_source_conflict() -> None:
    result = BoundaryResolver(FakeBoundaryRepository((membership(1), membership(2)))).resolve(
        longitude=-97.90,
        latitude=31.11,
        effective_on=date(2026, 11, 3),
    )

    assert result.status is BoundaryResolutionStatus.SOURCE_CONFLICT
    assert result.reasons == (BoundaryResolutionReason.OVERLAPPING_VERIFIED_BOUNDARIES,)


def test_no_match_and_invalid_coordinates_are_explicit() -> None:
    result = BoundaryResolver(FakeBoundaryRepository(())).resolve(
        longitude=-97.90,
        latitude=31.11,
        effective_on=date(2026, 11, 3),
    )
    assert result.status is BoundaryResolutionStatus.NOT_FOUND
    assert result.reasons == (BoundaryResolutionReason.NO_BOUNDARY_MATCH,)

    with pytest.raises(ValueError, match="longitude"):
        BoundaryResolver(FakeBoundaryRepository(())).resolve(
            longitude=181,
            latitude=31.11,
            effective_on=date(2026, 11, 3),
        )
