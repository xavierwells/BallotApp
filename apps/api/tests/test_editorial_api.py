from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.editorial_auth import hash_password, verify_password
from app.main import app

client = TestClient(app)


@pytest.mark.parametrize("path", ["me", "batches", f"batches/{uuid4()}", f"batches/{uuid4()}/source",
                                  "guide-preview", f"guide-preview/{uuid4()}"])
def test_editorial_reads_require_login_and_are_not_cached(path):
    response = client.get(f"/api/v1/editorial/{path}")
    assert response.status_code == 401
    assert "no-store" in response.headers["cache-control"]


def test_login_requires_trusted_browser_origin():
    response = client.post("/api/v1/editorial/login", json={"username": "reviewer", "password": "synthetic-passphrase"},
                           headers={"Origin": "https://other.example"})
    assert response.status_code == 403


def test_password_validation_never_reflects_credentials():
    value = "private-test-value" * 25
    response = client.post("/api/v1/editorial/login", json={"username": "reviewer", "password": value},
                           headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 422
    assert value not in response.text


def test_editorial_openapi_describes_session_auth_and_decisions():
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/api/v1/editorial/batches"]["get"]["security"]
    assert "ReviewRequest" in schema["components"]["schemas"]
    assert "raceKeys" in schema["components"]["schemas"]["ReviewRequest"]["properties"]
    assert "pdfPageNumber" in schema["components"]["schemas"]["Race"]["properties"]
    assert "409" in schema["paths"]["/api/v1/editorial/batches/{batch_id}/decisions"]["post"]["responses"]
    review = schema["paths"]["/api/v1/editorial/batches/{batch_id}/review"]["post"]
    assert review["security"]
    assert "409" in review["responses"]
    assert "sections" in schema["components"]["schemas"]["SectionReviewRequest"]["properties"]
    assert "confirmed" in schema["components"]["schemas"]["SectionReviewRequest"]["required"]
    assert "corrections" in schema["components"]["schemas"]["Race"]["properties"]
    assert "carriedForward" in schema["components"]["schemas"]["Decision"]["properties"]
    assert "sharedReviews" in schema["components"]["schemas"]["Race"]["properties"]
    assert "countySourceReviewed" in schema["components"]["schemas"]["Race"]["properties"]
    assert "requiresCountyConfirmation" in schema["components"]["schemas"]["Batch"]["properties"]
    assert "reviewBasisHash" in schema["components"]["schemas"]["ImportReviewRequest"]["properties"]
    for path in ("/api/v1/editorial/guide-preview", "/api/v1/editorial/guide-preview/{batch_id}"):
        assert schema["paths"][path]["get"]["security"]
        assert list(schema["paths"][path]) == ["get"]
    assert "409" in schema["paths"]["/api/v1/editorial/guide-preview/{batch_id}"]["get"]["responses"]
    assert schema["components"]["schemas"]["GuidePreview"]["properties"]["exactMatch"]["const"] is False


def test_passwords_have_unique_salts_and_validate():
    first = hash_password("synthetic strong passphrase")
    second = hash_password("synthetic strong passphrase")
    assert first != second
    assert verify_password("synthetic strong passphrase", first)
    assert not verify_password("different passphrase", first)


def test_new_staff_password_requires_a_passphrase():
    with pytest.raises(ValueError, match="15"):
        hash_password("short")
