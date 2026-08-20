from datetime import datetime, timezone

import pytest

from app.cli.queue_overdue_source_alerts import queue_overdue_alerts
from app.cli.record_source_check import parse_utc_datetime, record_source_check
from app.cli.review_source import review_source


class FakeResult:
    def __init__(self, *, mapping: dict[str, str] | None = None, scalar: str | None = None, scalars: list[str] | None = None):
        self.mapping = mapping
        self.scalar = scalar
        self.scalar_values = scalars or []

    def mappings(self) -> "FakeResult":
        return self

    def one_or_none(self) -> dict[str, str] | None:
        return self.mapping

    def scalar_one(self) -> str:
        assert self.scalar is not None
        return self.scalar

    def scalars(self) -> "FakeResult":
        return self

    def all(self) -> list[str]:
        return self.scalar_values


class FakeConnection:
    def __init__(self, results: list[FakeResult]):
        self.results = results
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, statement: object, parameters: dict[str, object]) -> FakeResult:
        self.calls.append((str(statement), parameters))
        return self.results.pop(0)


class FakeTransaction:
    def __init__(self, connection: FakeConnection):
        self.connection = connection

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False


class FakeEngine:
    def __init__(self, connection: FakeConnection):
        self.connection = connection

    def begin(self) -> FakeTransaction:
        return FakeTransaction(self.connection)


def test_record_source_check_scopes_the_lookup_and_inserts_a_manual_check() -> None:
    connection = FakeConnection(
        [
            FakeResult(
                mapping={"id": "source-id", "approval_status": "pending_review", "permitted_use": "direct_link_manual_check"}
            ),
            FakeResult(scalar="check-id"),
        ]
    )
    checked_at = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    next_check_at = datetime(2026, 8, 27, 12, tzinfo=timezone.utc)

    check_id = record_source_check(
        engine=FakeEngine(connection),  # type: ignore[arg-type]
        organization_slug="test-organization",
        publication_slug="test-publication",
        authority_slug="test-authority",
        source_slug="elections",
        result="unchanged",
        checker_reference="editor-123",
        checked_at=checked_at,
        next_check_at=next_check_at,
        notes=None,
    )

    assert check_id == "check-id"
    assert connection.calls[0][1]["organization_slug"] == "test-organization"
    assert "check_method" in connection.calls[1][0]
    assert connection.calls[1][1]["next_check_at"] == next_check_at


def test_record_source_check_rejects_sources_without_a_permitted_use() -> None:
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    unapproved_connection = FakeConnection(
        [FakeResult(mapping={"id": "source-id", "approval_status": "pending_review", "permitted_use": "none"})]
    )

    with pytest.raises(ValueError, match="does not permit"):
        record_source_check(
            engine=FakeEngine(unapproved_connection),  # type: ignore[arg-type]
            organization_slug="organization",
            publication_slug="publication",
            authority_slug="authority",
            source_slug="source",
            result="unchanged",
            checker_reference="editor",
            checked_at=now,
            next_check_at=now,
            notes=None,
        )


def test_queue_overdue_alerts_is_timestamp_only_and_returns_created_count() -> None:
    connection = FakeConnection([FakeResult(scalars=["alert-1", "alert-2"])])
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)

    assert queue_overdue_alerts(engine=FakeEngine(connection), now=now) == 2  # type: ignore[arg-type]
    statement, parameters = connection.calls[0]
    assert "approval_status IN ('pending_review', 'approved')" in statement
    assert "permitted_use IN ('direct_link_manual_check', 'private_retention', 'public_copy')" in statement
    assert "monitoring_class <> 'disabled'" in statement
    assert "ON CONFLICT DO NOTHING" in statement
    assert parameters == {"now": now}


def test_review_source_requires_complete_terms_before_approval() -> None:
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="source_license"):
        review_source(
            engine=FakeEngine(FakeConnection([])),  # type: ignore[arg-type]
            organization_slug="organization",
            publication_slug="publication",
            authority_slug="authority",
            source_slug="source",
            approval_status="approved",
            permitted_use="private_retention",
            reviewer_reference="editor",
            reviewed_at=now,
            review_notes=None,
            terms_url="https://example.test/terms",
            source_license=None,
            cost_model="free",
            rate_limit="manual only",
            retention_rule="retain privately",
            attribution_requirement="cite source",
            redistribution_rights="metadata only",
            next_review_at=None,
            automated_monitoring_allowed=False,
        )


def test_review_source_rejects_automation_for_an_unapproved_decision() -> None:
    now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="only for an approved source"):
        review_source(
            engine=FakeEngine(FakeConnection([])),  # type: ignore[arg-type]
            organization_slug="organization",
            publication_slug="publication",
            authority_slug="authority",
            source_slug="source",
            approval_status="rejected",
            permitted_use="none",
            reviewer_reference="editor",
            reviewed_at=now,
            review_notes=None,
            terms_url=None,
            source_license=None,
            cost_model=None,
            rate_limit=None,
            retention_rule=None,
            attribution_requirement=None,
            redistribution_rights=None,
            next_review_at=None,
            automated_monitoring_allowed=True,
        )


def test_timestamp_parser_requires_an_offset_and_normalizes_to_utc() -> None:
    assert parse_utc_datetime("2026-08-20T07:00:00-05:00") == datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    with pytest.raises(Exception, match="must include a UTC offset"):
        parse_utc_datetime("2026-08-20T12:00:00")
