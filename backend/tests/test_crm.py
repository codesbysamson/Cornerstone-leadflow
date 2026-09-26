"""Staff CRM endpoints: lead list and status update.

The customer quote flow in test_leads.py is the regression contract for the
public API and must keep passing unchanged.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Lead
from app.schemas import LeadStatus

ENQUIRY = {
    "customer_name": "Sarah Johnson",
    "email": "sarah@example.com",
    "phone": "+44 7700 900123",
    "service": "Commercial Cleaning",
    "property_type": "Office",
    "location": "Lagos",
}


def make_lead(session: Session, name: str, created_at: datetime | None = None) -> Lead:
    """Inserts a lead directly so ordering can be controlled exactly."""
    lead = Lead(
        customer_name=name,
        email=f"{name.split()[0].lower()}@example.com",
        phone="+44 7700 900000",
        service="Commercial Cleaning",
        property_type="Office",
        location="Lagos",
    )
    if created_at is not None:
        lead.created_at = created_at
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


def test_list_leads_returns_empty_list(client: TestClient) -> None:
    response = client.get("/api/leads")

    assert response.status_code == 200
    assert response.json() == []


def test_list_leads_returns_multiple_leads(client: TestClient) -> None:
    for name in ("Sarah Johnson", "Daniel Okoro", "Priya Raman"):
        response = client.post("/api/leads", json={**ENQUIRY, "customer_name": name})
        assert response.status_code == 201

    response = client.get("/api/leads")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert {lead["customer_name"] for lead in body} == {
        "Sarah Johnson",
        "Daniel Okoro",
        "Priya Raman",
    }
    # The list reuses LeadRead, so the full enquiry is present on every row.
    assert body[0]["service"] == "Commercial Cleaning"
    assert body[0]["source"] == "WEBSITE"
    assert body[0]["status"] == "NEW"


def test_list_leads_is_ordered_newest_first(
    client: TestClient, session: Session
) -> None:
    make_lead(session, "Oldest Lead", datetime(2026, 1, 1, 9, 0, tzinfo=UTC))
    make_lead(session, "Newest Lead", datetime(2026, 9, 20, 9, 0, tzinfo=UTC))
    make_lead(session, "Middle Lead", datetime(2026, 5, 11, 9, 0, tzinfo=UTC))

    response = client.get("/api/leads")

    assert response.status_code == 200
    assert [lead["customer_name"] for lead in response.json()] == [
        "Newest Lead",
        "Middle Lead",
        "Oldest Lead",
    ]


def test_update_status_returns_updated_lead(client: TestClient, session: Session) -> None:
    lead = make_lead(session, "Sarah Johnson")

    response = client.post(f"/api/leads/{lead.id}/status", json={"status": "CONTACTED"})

    assert response.status_code == 200
    assert response.json()["status"] == "CONTACTED"
    assert response.json()["id"] == lead.id


def test_update_status_is_persisted(client: TestClient, session: Session) -> None:
    lead = make_lead(session, "Sarah Johnson")

    client.post(f"/api/leads/{lead.id}/status", json={"status": "QUALIFIED"})

    # Expire the identity map so the read comes from the database rather than
    # the already-loaded in-session object.
    session.expire_all()
    assert session.get(Lead, lead.id).status == "QUALIFIED"


def test_update_status_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.post("/api/leads/999999/status", json={"status": "CONTACTED"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Lead 999999 not found"}


def test_update_status_with_invalid_status_returns_422(client: TestClient) -> None:
    response = client.post("/api/leads/1/status", json={"status": "BOGUS"})

    assert response.status_code == 422


def test_update_status_without_status_returns_422(client: TestClient) -> None:
    response = client.post("/api/leads/1/status", json={})

    assert response.status_code == 422


def test_update_status_with_extra_field_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/leads/1/status",
        json={"status": "CONTACTED", "customer_name": "Injected"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("value", [member.value for member in LeadStatus])
def test_every_planned_status_is_accepted(
    client: TestClient, session: Session, value: str
) -> None:
    lead = make_lead(session, "Sarah Johnson")

    response = client.post(f"/api/leads/{lead.id}/status", json={"status": value})

    assert response.status_code == 200
    assert response.json()["status"] == value


def test_update_status_leaves_enquiry_untouched(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session, "Sarah Johnson")

    client.post(f"/api/leads/{lead.id}/status", json={"status": "WON"})

    updated = client.get(f"/api/leads/{lead.id}").json()
    assert updated["customer_name"] == "Sarah Johnson"
    assert updated["service"] == "Commercial Cleaning"
    assert updated["location"] == "Lagos"
    assert updated["source"] == "WEBSITE"
