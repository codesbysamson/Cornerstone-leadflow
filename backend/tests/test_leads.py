from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lead

VALID_ENQUIRY = {
    "customer_name": "Sarah Johnson",
    "email": "sarah@example.com",
    "phone": "+44 7700 900123",
    "service": "Office Cleaning",
    "property_type": "Office",
    "location": "Manchester",
    "property_size": "2,500 sq ft",
    "frequency": "Weekly",
    "preferred_date": "2026-10-05",
    "requirements": "Cleaning required outside normal office hours.",
}


def test_create_lead_returns_201_and_persists(
    public_client: TestClient, session: Session
) -> None:
    response = public_client.post("/api/leads", json=VALID_ENQUIRY)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["status"] == "NEW"
    assert body["source"] == "WEBSITE"
    assert body["created_at"] is not None

    stored = session.execute(select(Lead)).scalar_one()
    assert stored.id == body["id"]
    assert stored.customer_name == "Sarah Johnson"
    assert stored.email == "sarah@example.com"


def test_created_lead_can_be_retrieved(
    client: TestClient, public_client: TestClient
) -> None:
    """The public enquiry and the staff CRM meeting end to end.

    Submitted with no session at all, then read back with one: if the split
    between the two routers is wrong, this fails.
    """
    created = public_client.post("/api/leads", json=VALID_ENQUIRY).json()

    response = client.get(f"/api/leads/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    for field in (
        "customer_name",
        "email",
        "phone",
        "service",
        "property_type",
        "location",
        "property_size",
        "frequency",
        "preferred_date",
        "requirements",
    ):
        assert body[field] == VALID_ENQUIRY[field]


def test_create_lead_without_required_field_returns_422(public_client: TestClient) -> None:
    payload = {key: value for key, value in VALID_ENQUIRY.items() if key != "location"}

    response = public_client.post("/api/leads", json=payload)

    assert response.status_code == 422


def test_create_lead_with_invalid_email_returns_422(public_client: TestClient) -> None:
    payload = {**VALID_ENQUIRY, "email": "not-an-email"}

    response = public_client.post("/api/leads", json=payload)

    assert response.status_code == 422


def test_get_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.get("/api/leads/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Lead 999999 not found"}


def test_client_cannot_override_system_owned_fields(
    public_client: TestClient, session: Session
) -> None:
    payload = {
        **VALID_ENQUIRY,
        "id": 4242,
        "status": "WON",
        "source": "MANUAL",
        "created_at": "1999-01-01T00:00:00Z",
    }

    response = public_client.post("/api/leads", json=payload)

    assert response.status_code == 422

    stored = session.execute(select(Lead)).scalars().all()
    assert stored == []
