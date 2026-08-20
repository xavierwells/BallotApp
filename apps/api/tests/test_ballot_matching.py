from datetime import date
from uuid import UUID

from app.ballot_matching import BallotMatcher, BallotMatchStatus


PUBLICATION_ID = UUID("00000000-0000-0000-0000-000000000001")
ELECTION_ID = UUID("00000000-0000-0000-0000-000000000002")
AREA_IDS = frozenset(
    {
        UUID("00000000-0000-0000-0000-000000000010"),
        UUID("00000000-0000-0000-0000-000000000011"),
    }
)


class FakeRepository:
    def __init__(self, matches: tuple[UUID, ...]) -> None:
        self.matches = matches
        self.received_area_ids: frozenset[UUID] | None = None

    def matching_ballots(self, **arguments: object) -> tuple[UUID, ...]:
        self.received_area_ids = arguments["geographic_area_ids"]  # type: ignore[assignment]
        return self.matches


def test_combination_match_allows_unrelated_extra_memberships() -> None:
    ballot_id = UUID("00000000-0000-0000-0000-000000000100")
    repository = FakeRepository((ballot_id,))
    result = BallotMatcher(repository).match(
        publication_id=PUBLICATION_ID,
        election_id=ELECTION_ID,
        effective_on=date(2026, 11, 3),
        geographic_area_ids=AREA_IDS,
    )

    assert result.status is BallotMatchStatus.MATCHED
    assert result.ballot_version_ids == (ballot_id,)
    assert repository.received_area_ids == AREA_IDS


def test_zero_and_multiple_combinations_never_choose_a_winner() -> None:
    no_match = BallotMatcher(FakeRepository(())).match(
        publication_id=PUBLICATION_ID,
        election_id=ELECTION_ID,
        effective_on=date(2026, 11, 3),
        geographic_area_ids=AREA_IDS,
    )
    multiple = BallotMatcher(
        FakeRepository(
            (
                UUID("00000000-0000-0000-0000-000000000100"),
                UUID("00000000-0000-0000-0000-000000000101"),
            )
        )
    ).match(
        publication_id=PUBLICATION_ID,
        election_id=ELECTION_ID,
        effective_on=date(2026, 11, 3),
        geographic_area_ids=AREA_IDS,
    )

    assert no_match.status is BallotMatchStatus.NOT_FOUND
    assert multiple.status is BallotMatchStatus.MULTIPLE_MATCHES
    assert len(multiple.ballot_version_ids) == 2
