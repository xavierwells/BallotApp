"""Match a verified jurisdiction combination to a published ballot version."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine


class BallotMatchStatus(StrEnum):
    MATCHED = "matched"
    NOT_FOUND = "not_found"
    MULTIPLE_MATCHES = "multiple_matches"


@dataclass(frozen=True)
class BallotMatch:
    status: BallotMatchStatus
    ballot_version_ids: tuple[UUID, ...]


class BallotRequirementRepository(Protocol):
    def matching_ballots(
        self,
        *,
        publication_id: UUID,
        election_id: UUID,
        effective_on: date,
        geographic_area_ids: frozenset[UUID],
    ) -> tuple[UUID, ...]: ...


class PostgresBallotRequirementRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def matching_ballots(
        self,
        *,
        publication_id: UUID,
        election_id: UUID,
        effective_on: date,
        geographic_area_ids: frozenset[UUID],
    ) -> tuple[UUID, ...]:
        if not geographic_area_ids:
            return ()
        statement = text(
            "SELECT bv.id FROM ballot_versions bv "
            "JOIN elections e ON e.id = bv.election_id AND e.publication_id = bv.publication_id "
            "JOIN ballot_geographic_requirements requirement ON requirement.ballot_version_id = bv.id "
            "AND requirement.publication_id = bv.publication_id "
            "WHERE bv.publication_id = :publication_id AND bv.election_id = :election_id "
            "AND bv.status = 'published' AND e.election_date = :effective_on "
            "GROUP BY bv.id "
            "HAVING COUNT(*) > 0 AND BOOL_AND(requirement.geographic_area_id IN :area_ids) "
            "ORDER BY bv.id"
        ).bindparams(bindparam("area_ids", expanding=True))
        with self.engine.connect() as connection:
            return tuple(
                row[0]
                for row in connection.execute(
                    statement,
                    {
                        "publication_id": publication_id,
                        "election_id": election_id,
                        "effective_on": effective_on,
                        "area_ids": tuple(geographic_area_ids),
                    },
                )
            )


class BallotMatcher:
    def __init__(self, repository: BallotRequirementRepository) -> None:
        self.repository = repository

    def match(
        self,
        *,
        publication_id: UUID,
        election_id: UUID,
        effective_on: date,
        geographic_area_ids: frozenset[UUID],
    ) -> BallotMatch:
        matches = self.repository.matching_ballots(
            publication_id=publication_id,
            election_id=election_id,
            effective_on=effective_on,
            geographic_area_ids=geographic_area_ids,
        )
        if not matches:
            return BallotMatch(BallotMatchStatus.NOT_FOUND, ())
        if len(matches) > 1:
            return BallotMatch(BallotMatchStatus.MULTIPLE_MATCHES, matches)
        return BallotMatch(BallotMatchStatus.MATCHED, matches)
