from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from app.main import app
from app.schemas.ballot_resolution import BallotBrowseResponse, MultipleBallotsResponse

client = TestClient(app)


def test_openapi_contract_is_published() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/ballots/resolve" in response.json()["paths"]
    assert "/api/v1/ballots/resolve-preview" in response.json()["paths"]
    assert response.json()["paths"]["/api/v1/ballots/resolve-preview"]["post"]["deprecated"] is True
    assert "/api/v1/ballots/browse" in response.json()["paths"]
    browse_operation = response.json()["paths"]["/api/v1/ballots/browse"]["get"]
    assert any(parameter["name"] == "areaType" for parameter in browse_operation["parameters"])


def test_address_preview_explicitly_does_not_persist_address() -> None:
    response = client.post(
        "/api/v1/ballots/resolve",
        json={"address": "914 Example Street, Copperas Cove, TX 76522"},
    )

    assert response.status_code == 200
    assert response.json()["addressPersisted"] is False
    assert response.json()["status"] == "not_available"
    assert "914 Example Street" not in response.text


def test_address_preview_rejects_an_invalid_address() -> None:
    response = client.post(
        "/api/v1/ballots/resolve-preview",
        json={"address": "no"},
    )

    assert response.status_code == 422


def test_browse_contract_is_explicitly_not_an_exact_match() -> None:
    response = client.get(
        "/api/v1/ballots/browse",
        params={"areaType": "city", "query": "Copperas Cove"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "not_available",
        "areaType": "city",
        "query": "Copperas Cove",
        "exactMatch": False,
        "message": "Ballot browsing is not connected yet. No exact voter match was attempted.",
        "matches": [],
    }


def test_browse_contract_rejects_an_unsupported_area_type() -> None:
    response = client.get(
        "/api/v1/ballots/browse",
        params={"areaType": "precinct", "query": "1"},
    )

    assert response.status_code == 422


def test_available_browse_response_requires_a_ballot() -> None:
    with pytest.raises(ValidationError, match="available browse responses require"):
        BallotBrowseResponse(
            status="available",
            area_type="zip",
            query="76522",
            message="Choose a ballot to inspect.",
        )


def test_ambiguous_response_requires_at_least_two_unique_ballots() -> None:
    with pytest.raises(ValidationError):
        MultipleBallotsResponse(
            status="ambiguous",
            confidence=40,
            message="More than one ballot may apply.",
            plausible_ballots=[],
        )


def test_cors_preflight_allows_the_address_post_from_the_web_app() -> None:
    response = client.options(
        "/api/v1/ballots/resolve-preview",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert "POST" in response.headers["access-control-allow-methods"]
