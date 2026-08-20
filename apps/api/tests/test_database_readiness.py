from fastapi import HTTPException, status
import pytest

from app.routers import health


def test_readiness_succeeds_when_database_is_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "database_is_ready", lambda: True)

    assert health.ready() == {"status": "ready"}


def test_readiness_returns_503_when_database_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "database_is_ready", lambda: False)

    with pytest.raises(HTTPException) as error:
        health.ready()

    assert error.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert error.value.detail == "database unavailable"
