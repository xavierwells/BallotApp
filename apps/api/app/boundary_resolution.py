"""Request-scoped point-in-polygon resolution over verified civic boundaries.

Coordinates are accepted only as method arguments and are never included in a
result object, persisted, queued, or logged by this module.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine


class BoundaryResolutionStatus(StrEnum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    SOURCE_CONFLICT = "source_conflict"
    NOT_FOUND = "not_found"


class BoundaryResolutionReason(StrEnum):
    NO_BOUNDARY_MATCH = "no_boundary_match"
    ON_BOUNDARY_EDGE = "on_boundary_edge"
    OVERLAPPING_VERIFIED_BOUNDARIES = "overlapping_verified_boundaries"


@dataclass(frozen=True)
class BoundaryMembership:
    boundary_version_id: UUID
    geographic_area_id: UUID
    authority_id: UUID
    area_type: str
    area_name: str
    authority_name: str
    source_url: str
    source_checked_at: datetime
    source_label: str
    on_boundary_edge: bool

    @property
    def partition_key(self) -> tuple[UUID, str]:
        """Return the authority/type pair expected to contain one applicable area."""
        return self.authority_id, self.area_type


@dataclass(frozen=True)
class BoundaryResolution:
    status: BoundaryResolutionStatus
    memberships: tuple[BoundaryMembership, ...]
    reasons: tuple[BoundaryResolutionReason, ...]


class BoundaryRepository(Protocol):
    def memberships_at(
        self, *, longitude: float, latitude: float, effective_on: date, uncertainty_meters: float = 0
    ) -> tuple[BoundaryMembership, ...]: ...


class PostgisBoundaryRepository:
    """Read effective, verified boundaries using a parameterized PostGIS query."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def memberships_at(
        self, *, longitude: float, latitude: float, effective_on: date, uncertainty_meters: float = 0
    ) -> tuple[BoundaryMembership, ...]:
        point_sql = "ST_SetSRID(ST_Point(:longitude, :latitude), 4326)"
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT bv.id AS boundary_version_id, ga.id AS geographic_area_id, "
                    "bv.authority_id, ga.area_type, ga.name AS area_name, "
                    "subject.name AS authority_name, bd.source_url, bd.checked_at AS source_checked_at, "
                    "publisher.name || ' boundary dataset' AS source_label, "
                    f"(ST_Touches(bv.boundary, {point_sql}) OR ST_DWithin("
                    f"ST_Boundary(bv.boundary)::geography, {point_sql}::geography, :uncertainty_meters"
                    ")) AS on_boundary_edge "
                    "FROM boundary_versions bv "
                    "JOIN geographic_areas ga ON ga.id = bv.geographic_area_id "
                    "AND ga.authority_id = bv.authority_id "
                    "JOIN boundary_datasets bd ON bd.id = bv.boundary_dataset_id "
                    "AND bd.subject_authority_id = bv.authority_id "
                    "JOIN election_authorities subject ON subject.id = bv.authority_id "
                    "JOIN election_authorities publisher ON publisher.id = bd.publisher_authority_id "
                    "WHERE bv.status = 'verified' AND ga.status = 'active' "
                    "AND bv.effective_from <= :effective_on "
                    "AND (bv.effective_to IS NULL OR bv.effective_to >= :effective_on) "
                    f"AND ST_Covers(bv.boundary, {point_sql}) "
                    "ORDER BY ga.area_type, ga.name, bv.id"
                ),
                {
                    "longitude": longitude,
                    "latitude": latitude,
                    "effective_on": effective_on,
                    "uncertainty_meters": uncertainty_meters,
                },
            ).mappings()
            return tuple(BoundaryMembership(**row) for row in rows)


class BoundaryResolver:
    def __init__(self, repository: BoundaryRepository) -> None:
        self.repository = repository

    def resolve(
        self, *, longitude: float, latitude: float, effective_on: date, uncertainty_meters: float = 0
    ) -> BoundaryResolution:
        _validate_coordinates(longitude=longitude, latitude=latitude)
        if not 0 <= uncertainty_meters <= 10_000:
            raise ValueError("coordinate uncertainty must be between 0 and 10000 meters")
        memberships = self.repository.memberships_at(
            longitude=longitude,
            latitude=latitude,
            effective_on=effective_on,
            uncertainty_meters=uncertainty_meters,
        )
        if not memberships:
            return BoundaryResolution(
                status=BoundaryResolutionStatus.NOT_FOUND,
                memberships=(),
                reasons=(BoundaryResolutionReason.NO_BOUNDARY_MATCH,),
            )

        partition_counts = Counter(item.partition_key for item in memberships if not item.on_boundary_edge)
        if any(count > 1 for count in partition_counts.values()):
            return BoundaryResolution(
                status=BoundaryResolutionStatus.SOURCE_CONFLICT,
                memberships=memberships,
                reasons=(BoundaryResolutionReason.OVERLAPPING_VERIFIED_BOUNDARIES,),
            )
        if any(item.on_boundary_edge for item in memberships):
            return BoundaryResolution(
                status=BoundaryResolutionStatus.AMBIGUOUS,
                memberships=memberships,
                reasons=(BoundaryResolutionReason.ON_BOUNDARY_EDGE,),
            )
        return BoundaryResolution(
            status=BoundaryResolutionStatus.MATCHED,
            memberships=memberships,
            reasons=(),
        )


def _validate_coordinates(*, longitude: float, latitude: float) -> None:
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")
