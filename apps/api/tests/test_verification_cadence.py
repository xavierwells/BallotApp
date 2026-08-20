from datetime import date, timedelta

from app.verification_cadence import BUILT_IN_CADENCE, MonitoringClass, VerificationCadence, resolve_cadence


def test_builtin_cadence_matches_the_approved_stage_policy() -> None:
    today = date(2026, 8, 20)

    assert BUILT_IN_CADENCE.interval_for(
        today=today, next_election_date=None, official_ballot_available=False, monitoring_class=MonitoringClass.REFERENCE
    ) == timedelta(days=30)
    assert BUILT_IN_CADENCE.interval_for(
        today=today,
        next_election_date=date(2026, 11, 3),
        official_ballot_available=False,
        monitoring_class=MonitoringClass.ACTIVE_ELECTION,
    ) == timedelta(days=7)
    assert BUILT_IN_CADENCE.interval_for(
        today=today,
        next_election_date=date(2026, 11, 3),
        official_ballot_available=True,
        monitoring_class=MonitoringClass.ACTIVE_BALLOT,
    ) == timedelta(days=1)
    assert BUILT_IN_CADENCE.interval_for(
        today=today,
        next_election_date=date(2026, 11, 3),
        official_ballot_available=True,
        monitoring_class=MonitoringClass.ACTIVE_ELECTION,
    ) == timedelta(days=7)
    assert BUILT_IN_CADENCE.interval_for(
        today=today,
        next_election_date=date(2026, 11, 3),
        official_ballot_available=True,
        monitoring_class=MonitoringClass.DISABLED,
    ) is None


def test_more_specific_cadence_replaces_the_less_specific_policy() -> None:
    organization = VerificationCadence(ordinary_interval_hours=720)
    publication = VerificationCadence(ordinary_interval_hours=240)
    authority = VerificationCadence(ordinary_interval_hours=48)

    assert resolve_cadence(organization=organization, publication=publication, authority=authority) == authority
    assert resolve_cadence(organization=organization, publication=publication, authority=None) == publication
    assert resolve_cadence(organization=organization, publication=None, authority=None) == organization
