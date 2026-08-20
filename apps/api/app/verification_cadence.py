"""Policy resolution for source verification without hard-coded tenant rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class MonitoringClass(StrEnum):
    """How a source participates in the editorial freshness workflow."""

    ACTIVE_BALLOT = "active_ballot"
    ACTIVE_ELECTION = "active_election"
    REFERENCE = "reference"
    DISABLED = "disabled"


@dataclass(frozen=True)
class VerificationCadence:
    """Intervals governing a source's next review deadline."""

    ordinary_interval_hours: int = 24 * 30
    active_window_days: int = 90
    active_interval_hours: int = 24 * 7
    official_ballot_interval_hours: int = 24

    def interval_for(
        self,
        *,
        today: date,
        next_election_date: date | None,
        official_ballot_available: bool,
        monitoring_class: MonitoringClass,
    ) -> timedelta | None:
        """Return the re-verification interval for the current election stage."""
        if monitoring_class is MonitoringClass.DISABLED:
            return None
        election_is_active = (
            next_election_date is not None
            and today <= next_election_date <= today + timedelta(days=self.active_window_days)
        )
        if (
            election_is_active
            and official_ballot_available
            and monitoring_class is MonitoringClass.ACTIVE_BALLOT
        ):
            return timedelta(hours=self.official_ballot_interval_hours)
        if election_is_active and monitoring_class in {
            MonitoringClass.ACTIVE_BALLOT,
            MonitoringClass.ACTIVE_ELECTION,
        }:
            return timedelta(hours=self.active_interval_hours)
        return timedelta(hours=self.ordinary_interval_hours)


BUILT_IN_CADENCE = VerificationCadence()


def resolve_cadence(
    *,
    organization: VerificationCadence | None,
    publication: VerificationCadence | None,
    authority: VerificationCadence | None,
) -> VerificationCadence:
    """Resolve the most-specific configured cadence without merging policies."""
    return authority or publication or organization or BUILT_IN_CADENCE
