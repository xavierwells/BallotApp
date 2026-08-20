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
    assert '"input"' not in response.text
    assert "no" not in response.text


def test_address_validation_does_not_echo_a_long_submitted_value() -> None:
    submitted_value = "Synthetic Private Address " + ("x" * 300)
    response = client.post(
        "/api/v1/ballots/resolve",
        json={"address": submitted_value},
    )

    assert response.status_code == 422
    assert submitted_value not in response.text


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
        "demonstration": False,
        "message": "Ballot browsing is not connected yet. No exact voter match was attempted.",
        "matches": [],
    }


def test_browse_contract_rejects_an_unsupported_area_type() -> None:
    response = client.get(
        "/api/v1/ballots/browse",
        params={"areaType": "precinct", "query": "1"},
    )

    assert response.status_code == 422


def test_browse_contract_rejects_an_invalid_zip_without_echoing_it() -> None:
    response = client.get(
        "/api/v1/ballots/browse",
        params={"areaType": "zip", "query": "private street text"},
    )

    assert response.status_code == 422
    assert "private street text" not in response.text


def test_available_browse_response_requires_a_ballot() -> None:
    with pytest.raises(ValidationError, match="available browse responses require"):
        BallotBrowseResponse(
            status="available",
            area_type="zip",
            query="76522",
            message="Choose a ballot to inspect.",
        )


def test_browse_ranking_rejects_an_unsourced_most_common_claim() -> None:
    with pytest.raises(ValidationError, match="calculation basis and source"):
        BallotBrowseResponse(
            status="available",
            area_type="zip",
            query="76522",
            message="Synthetic ranking.",
            matches=[
                {
                    "ballot": {
                        "ballot_version_id": "00000000-0000-0000-0000-000000000001",
                        "label": "Synthetic ballot",
                        "election_name": "Synthetic election",
                        "election_date": "2026-11-03",
                        "official_source": {
                            "authority_name": "Synthetic authority",
                            "source_url": "https://example.test/ballot",
                            "checked_at": "2026-08-20T00:00:00Z",
                            "source_label": "Synthetic source",
                        },
                    },
                    "geographic_support": [{
                        "geographic_area_id": "00000000-0000-0000-0000-000000000002",
                        "area_type": "zip",
                        "name": "Synthetic ZIP",
                        "boundary_version_id": "00000000-0000-0000-0000-000000000003",
                        "explanation": "Synthetic support.",
                        "source": {
                            "authority_name": "Synthetic authority",
                            "source_url": "https://example.test/boundary",
                            "checked_at": "2026-08-20T00:00:00Z",
                            "source_label": "Synthetic boundary",
                        },
                    }],
                    "relationship": "overlaps",
                    "rank": 1,
                    "estimated_area_share_percent": 95,
                    "coverage_basis": "residential_population_estimate",
                    "most_common_area_match": True,
                    "explanation": "Synthetic explanation.",
                }
            ],
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
