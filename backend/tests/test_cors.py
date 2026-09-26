"""Verifies the CORS policy the Vite dev server needs to call the API."""

import pytest
from fastapi.testclient import TestClient

from app.main import allowed_origins, app

ALLOWED_ORIGIN = "http://localhost:5173"
DISALLOWED_ORIGIN = "https://untrusted.example.com"

ENQUIRY = {
    "customer_name": "Sarah Johnson",
    "email": "sarah@example.com",
    "phone": "+44 7700 900123",
    "service": "Office Cleaning",
    "property_type": "Office",
    "location": "Manchester",
}


@pytest.fixture
def cors_client() -> TestClient:
    return TestClient(app)


def test_default_origins_cover_the_vite_dev_server() -> None:
    assert ALLOWED_ORIGIN in allowed_origins
    assert "http://127.0.0.1:5173" in allowed_origins


def test_no_wildcard_origin_is_configured() -> None:
    assert "*" not in allowed_origins


def test_preflight_from_allowed_origin_is_accepted(cors_client: TestClient) -> None:
    response = cors_client.options(
        "/api/leads",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]


def test_preflight_from_unknown_origin_is_not_allowed(cors_client: TestClient) -> None:
    response = cors_client.options(
        "/api/leads",
        headers={
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_creating_a_lead_from_allowed_origin_is_cors_permitted(
    client: TestClient,
) -> None:
    response = client.post("/api/leads", json=ENQUIRY, headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
