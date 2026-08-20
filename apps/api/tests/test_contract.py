from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_openapi_contract_is_published() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/ballots/resolve-preview" in response.json()["paths"]


def test_address_preview_explicitly_does_not_persist_address() -> None:
    response = client.post(
        "/api/v1/ballots/resolve-preview",
        json={"address": "914 Example Street, Copperas Cove, TX 76522"},
    )

    assert response.status_code == 200
    assert response.json()["addressPersisted"] is False


def test_address_preview_rejects_an_invalid_address() -> None:
    response = client.post(
        "/api/v1/ballots/resolve-preview",
        json={"address": "no"},
    )

    assert response.status_code == 422


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
