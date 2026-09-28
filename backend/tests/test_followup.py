"""Next follow-up: set, reschedule and clear.

Uses an explicit UTC offset throughout. The naive-datetime rejection is the
most important test in this milestone: a naive value written to a TIMESTAMPTZ
column is silently interpreted in the database server's zone, which corrupts
the stored instant while appearing to succeed.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.models import Lead
from app.schemas import LeadStatus

ENQUIRY = {
    "customer_name": "Sarah Johnson",
    "email": "sarah@example.com",
    "phone": "+44 7700 900123",
    "service": "Commercial Cleaning",
    "property_type": "Office",
    "location": "Manchester",
}

# The SQLite test database returns a naive timestamp while PostgreSQL returns
# an offset-aware one. Both carry the same UTC wall clock for these values, so
# comparing the leading characters asserts the stored instant on either backend.
STORED_PREFIX = "2026-10-05T14:30:00"


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


def test_new_lead_has_no_follow_up(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    body = client.get(f"/api/leads/{lead.id}").json()

    assert body["next_follow_up_at"] is None
    assert body["next_follow_up_action"] is None


def test_list_leads_exposes_follow_up_fields(
    client: TestClient, session: Session
) -> None:
    """The dashboard and lead list read follow-up from the existing list call."""
    lead = make_lead(session)
    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Send revised quote"},
    )

    body = client.get("/api/leads").json()

    assert len(body) == 1
    assert body[0]["next_follow_up_at"].startswith(STORED_PREFIX)
    assert body[0]["next_follow_up_action"] == "Send revised quote"


def test_set_follow_up(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Send revised quote"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["next_follow_up_at"].startswith(STORED_PREFIX)
    assert body["next_follow_up_action"] == "Send revised quote"


def test_set_follow_up_is_persisted(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Site visit"},
    )

    session.expire_all()
    stored = session.get(Lead, lead.id)
    assert stored.next_follow_up_at.replace(tzinfo=UTC) == datetime(
        2026, 10, 5, 14, 30, tzinfo=UTC
    )
    assert stored.next_follow_up_action == "Site visit"


def test_reschedule_overwrites_both_fields(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Send revised quote"},
    )

    response = client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-07T09:00:00Z", "action": "Book site visit"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["next_follow_up_at"].startswith("2026-10-07T09:00:00")
    assert body["next_follow_up_action"] == "Book site visit"


def test_clear_follow_up_nulls_both_fields(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Site visit"},
    )

    response = client.post(f"/api/leads/{lead.id}/follow-up", json={"clear": True})

    assert response.status_code == 200
    body = response.json()
    assert body["next_follow_up_at"] is None
    assert body["next_follow_up_action"] is None


def test_clear_follow_up_is_persisted(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Site visit"},
    )

    client.post(f"/api/leads/{lead.id}/follow-up", json={"clear": True})

    session.expire_all()
    stored = session.get(Lead, lead.id)
    assert stored.next_follow_up_at is None
    assert stored.next_follow_up_action is None


def test_clear_on_lead_with_no_follow_up_is_a_no_op(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/follow-up", json={"clear": True})

    assert response.status_code == 200
    assert response.json()["next_follow_up_at"] is None


def test_set_after_clear_works(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Site visit"},
    )
    client.post(f"/api/leads/{lead.id}/follow-up", json={"clear": True})

    response = client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-11-02T11:00:00Z", "action": "Re-quote"},
    )

    assert response.status_code == 200
    assert response.json()["next_follow_up_action"] == "Re-quote"


def test_follow_up_on_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/leads/999999/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Call"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Lead 999999 not found"}


def test_clear_on_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.post("/api/leads/999999/follow-up", json={"clear": True})

    assert response.status_code == 404


@pytest.mark.parametrize(
    "due_at",
    [
        "2026-10-05T14:30",  # what a datetime-local control produces
        "2026-10-05 14:30:00",
        "2026-10-05",
    ],
)
def test_naive_datetime_is_rejected_with_422(
    client: TestClient, session: Session, due_at: str
) -> None:
    """The anti-corruption guard: a naive value must fail loudly, not silently."""
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/follow-up", json={"due_at": due_at, "action": "Call"}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "due_at",
    [
        "2026-10-05T14:30:00Z",
        "2026-10-05T14:30:00+00:00",
        "2026-10-05T15:30:00+01:00",
    ],
)
def test_aware_datetimes_are_accepted(
    client: TestClient, session: Session, due_at: str
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/follow-up", json={"due_at": due_at, "action": "Call"}
    )

    assert response.status_code == 200


def test_offset_datetime_stores_the_correct_utc_instant(
    client: TestClient, session: Session, engine: Engine
) -> None:
    """A +01:00 wall clock must be stored as 13:30 UTC, not 15:30.

    PostgreSQL normalises an offset-aware value to UTC when it is written to a
    TIMESTAMPTZ column. SQLite has no native timestamptz and simply stores the
    local wall clock, so this guarantee is only observable on PostgreSQL — run
    the suite with TEST_DATABASE_URL against Neon to cover it.
    """
    if engine.dialect.name != "postgresql":
        pytest.skip(
            "SQLite stores the local wall clock of an aware datetime without "
            "normalising to UTC; this guarantee is verified on PostgreSQL"
        )

    lead = make_lead(session)

    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T15:30:00+01:00", "action": "Call"},
    )

    session.expire_all()
    stored = session.get(Lead, lead.id)
    assert stored.next_follow_up_at.astimezone(UTC) == datetime(
        2026, 10, 5, 13, 30, tzinfo=UTC
    )


def test_set_and_clear_together_returns_422(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"clear": True, "due_at": "2026-10-05T14:30:00Z", "action": "Call"},
    )

    assert response.status_code == 422


def test_empty_follow_up_body_returns_422(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/follow-up", json={})

    assert response.status_code == 422


def test_follow_up_missing_action_returns_422(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/follow-up", json={"due_at": "2026-10-05T14:30:00Z"}
    )

    assert response.status_code == 422


def test_follow_up_blank_action_returns_422(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "   "},
    )

    assert response.status_code == 422


def test_follow_up_over_length_action_returns_422(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "x" * 256},
    )

    assert response.status_code == 422


def test_follow_up_leaves_enquiry_untouched(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Site visit"},
    )

    body = client.get(f"/api/leads/{lead.id}").json()
    assert body["customer_name"] == "Sarah Johnson"
    assert body["service"] == "Commercial Cleaning"
    assert body["status"] == "NEW"
    assert body["source"] == "WEBSITE"


@pytest.mark.parametrize("value", [member.value for member in LeadStatus])
def test_every_status_still_persists_with_a_follow_up_set(
    client: TestClient, session: Session, value: str
) -> None:
    """Regression: the follow-up columns must not disturb status persistence."""
    lead = make_lead(session)
    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Call"},
    )

    response = client.post(f"/api/leads/{lead.id}/status", json={"status": value})

    assert response.status_code == 200
    assert response.json()["status"] == value
    assert response.json()["next_follow_up_action"] == "Call"


def test_won_and_lost_leads_can_still_hold_a_follow_up(
    client: TestClient, session: Session
) -> None:
    """Closed leads are excluded from buckets at read time, not by clearing.

    The value is left intact so reopening a deal restores the reminder with no
    data loss.
    """
    lead = make_lead(session)

    client.post(
        f"/api/leads/{lead.id}/follow-up",
        json={"due_at": "2026-10-05T14:30:00Z", "action": "Call"},
    )
    client.post(f"/api/leads/{lead.id}/status", json={"status": "WON"})

    body = client.get(f"/api/leads/{lead.id}").json()
    assert body["status"] == "WON"
    assert body["next_follow_up_action"] == "Call"
