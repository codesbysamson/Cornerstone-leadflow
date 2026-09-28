"""Staff activity notes for a lead.

The public quote flow in test_leads.py is the regression contract for the
customer API and must keep passing unchanged.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Lead, LeadNote

ENQUIRY = {
    "customer_name": "Sarah Johnson",
    "email": "sarah@example.com",
    "phone": "+44 7700 900123",
    "service": "Commercial Cleaning",
    "property_type": "Office",
    "location": "Manchester",
}


def make_lead(session: Session, name: str = "Sarah Johnson") -> Lead:
    lead = Lead(
        customer_name=name,
        email=f"{name.split()[0].lower()}@example.com",
        phone="+44 7700 900123",
        service="Commercial Cleaning",
        property_type="Office",
        location="Manchester",
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


def make_note(session: Session, lead: Lead, body: str, created_at: datetime) -> LeadNote:
    """Inserts a note directly so ordering can be controlled exactly."""
    note = LeadNote(lead_id=lead.id, body=body, created_at=created_at)
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


def test_list_notes_returns_empty_list_for_lead_with_no_notes(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.get(f"/api/leads/{lead.id}/notes")

    assert response.status_code == 200
    assert response.json() == []


def test_create_note_returns_created_note(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/notes", json={"body": "Called, left a voicemail."}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["lead_id"] == lead.id
    assert body["body"] == "Called, left a voicemail."
    assert body["id"] > 0
    assert body["created_at"]


def test_create_note_is_persisted(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    client.post(f"/api/leads/{lead.id}/notes", json={"body": "Site visit booked."})

    # Expire the identity map so the read comes from the database rather than
    # the already-loaded in-session object.
    session.expire_all()
    stored = session.query(LeadNote).one()
    assert stored.body == "Site visit booked."


def test_list_notes_is_ordered_newest_first(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    make_note(session, lead, "Oldest note", datetime(2026, 1, 1, 9, 0, tzinfo=UTC))
    make_note(session, lead, "Newest note", datetime(2026, 9, 20, 9, 0, tzinfo=UTC))
    make_note(session, lead, "Middle note", datetime(2026, 5, 11, 9, 0, tzinfo=UTC))

    response = client.get(f"/api/leads/{lead.id}/notes")

    assert response.status_code == 200
    assert [note["body"] for note in response.json()] == [
        "Newest note",
        "Middle note",
        "Oldest note",
    ]


def test_notes_are_scoped_to_their_own_lead(
    client: TestClient, session: Session
) -> None:
    first = make_lead(session, "Sarah Johnson")
    second = make_lead(session, "Daniel Okoro")
    make_note(session, first, "Belongs to Sarah", datetime(2026, 2, 1, 9, 0, tzinfo=UTC))
    make_note(session, second, "Belongs to Daniel", datetime(2026, 2, 2, 9, 0, tzinfo=UTC))

    response = client.get(f"/api/leads/{first.id}/notes")

    assert [note["body"] for note in response.json()] == ["Belongs to Sarah"]


def test_notes_have_no_author_field(client: TestClient, session: Session) -> None:
    """Author is out of scope for this milestone; assert the shape stays honest."""
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/notes", json={"body": "Note"})

    assert set(response.json()) == {"id", "lead_id", "body", "created_at"}


def test_create_note_on_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.post("/api/leads/999999/notes", json={"body": "Note"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Lead 999999 not found"}


def test_list_notes_for_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.get("/api/leads/999999/notes")

    assert response.status_code == 404


@pytest.mark.parametrize("body", ["", "   ", "\n\t "])
def test_create_note_with_blank_body_returns_422(
    client: TestClient, session: Session, body: str
) -> None:
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/notes", json={"body": body})

    assert response.status_code == 422


def test_create_note_without_body_returns_422(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/notes", json={})

    assert response.status_code == 422


def test_create_note_over_length_limit_returns_422(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/notes", json={"body": "x" * 2001})

    assert response.status_code == 422


def test_create_note_at_length_limit_is_accepted(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/notes", json={"body": "x" * 2000})

    assert response.status_code == 201


def test_create_note_with_extra_field_returns_422(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/notes",
        json={"body": "Called", "author": "injected", "lead_id": 999},
    )

    assert response.status_code == 422


def test_creating_a_note_does_not_change_the_lead(
    client: TestClient, session: Session
) -> None:
    """A note is activity, not a mutation of the enquiry."""
    lead = make_lead(session)

    client.post(f"/api/leads/{lead.id}/notes", json={"body": "Called"})

    reloaded = client.get(f"/api/leads/{lead.id}").json()
    assert reloaded["status"] == "NEW"
    assert reloaded["customer_name"] == "Sarah Johnson"
    assert reloaded["next_follow_up_at"] is None
