"""Quotation workflow.

Covers the whole lifecycle: authoring a draft, the server being authoritative
for every money figure, the status state machine, and the single lead-status
side effect the business asked for.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Lead, Quotation, QuotationItem

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


def item(description: str = "Deep clean", quantity="2", unit_price="150.00") -> dict:
    return {"description": description, "quantity": quantity, "unit_price": unit_price}


def payload(**overrides) -> dict:
    body = {"currency": "GBP", "items": [item()], "notes": None, "discount": "0.00"}
    body.update(overrides)
    return body


def create_quotation(client: TestClient, lead_id: int, **overrides) -> dict:
    response = client.post(f"/api/leads/{lead_id}/quotations", json=payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Creation and authoritative calculation
# ---------------------------------------------------------------------------


def test_create_quotation_returns_draft_with_server_figures(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    body = create_quotation(client, lead.id)

    assert body["status"] == "DRAFT"
    assert body["lead_id"] == lead.id
    assert body["currency"] == "GBP"
    assert body["reference"] == f"Q-{body['id']:04d}"
    # 2 x 150.00
    assert body["subtotal"] == "300.00"
    assert body["discount"] == "0.00"
    assert body["total"] == "300.00"
    assert body["sent_at"] is None


def test_multiple_line_items_are_summed_by_the_server(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    body = create_quotation(
        client,
        lead.id,
        items=[
            item("Deep clean", "2", "150.00"),
            item("Carpet shampoo", "1", "85.50"),
            item("Window clean", "4", "22.25"),
        ],
    )

    assert len(body["items"]) == 3
    assert [i["line_total"] for i in body["items"]] == [
        "300.00",
        "85.50",
        "89.00",
    ]
    # 300.00 + 85.50 + 89.00
    assert body["subtotal"] == "474.50"
    assert body["total"] == "474.50"


def test_client_supplied_totals_are_rejected(
    client: TestClient, session: Session
) -> None:
    """The browser cannot assert a total, because the field is not accepted."""
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations",
        json={**payload(), "subtotal": "1.00", "total": "1.00"},
    )

    assert response.status_code == 422


def test_client_supplied_line_total_is_rejected(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations",
        json={**payload(), "items": [{**item(), "line_total": "1.00"}]},
    )

    assert response.status_code == 422


def test_discount_is_subtracted_from_the_subtotal(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    body = create_quotation(client, lead.id, discount="50.00")

    assert body["subtotal"] == "300.00"
    assert body["discount"] == "50.00"
    assert body["total"] == "250.00"


def test_discount_equal_to_subtotal_gives_zero_total(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    body = create_quotation(client, lead.id, discount="300.00")

    assert body["total"] == "0.00"


def test_currency_is_stored_and_returned_explicitly(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    body = create_quotation(client, lead.id, currency="NGN")

    assert body["currency"] == "NGN"
    # No symbol is baked into the stored value.
    assert body["total"] == "300.00"


def test_currency_defaults_to_gbp(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations", json={"items": [item()]}
    )

    assert response.status_code == 201
    assert response.json()["currency"] == "GBP"


def test_notes_are_stored(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    body = create_quotation(
        client, lead.id, notes="Prices exclude VAT. Valid for 30 days."
    )

    assert body["notes"] == "Prices exclude VAT. Valid for 30 days."


# ---------------------------------------------------------------------------
# Money correctness
# ---------------------------------------------------------------------------


def test_persisted_amounts_are_decimal_not_float(
    client: TestClient, session: Session
) -> None:
    """The classic float trap: 0.1 + 0.2 must be exactly 0.30."""
    lead = make_lead(session)

    create_quotation(
        client,
        lead.id,
        items=[item("A", "1", "0.10"), item("B", "1", "0.20")],
    )

    session.expire_all()
    stored = session.query(Quotation).one()
    assert isinstance(stored.subtotal, Decimal)
    assert stored.subtotal == Decimal("0.30")
    assert stored.total == Decimal("0.30")


def test_repeated_float_amounts_stay_exact(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    body = create_quotation(
        client,
        lead.id,
        items=[item(f"Task {n}", "1", "0.10") for n in range(10)],
    )

    assert body["subtotal"] == "1.00"
    assert body["total"] == "1.00"


def test_unit_price_with_sub_penny_precision_is_normalised(
    client: TestClient, session: Session
) -> None:
    """A unit price is money, so it is rounded to the currency scale first.

    19.995 is not a price that can be billed per unit in a two-decimal
    currency, so it becomes 20.00 before the quantity is applied.
    """
    lead = make_lead(session)

    body = create_quotation(client, lead.id, items=[item("Odd", "3", "19.995")])

    assert body["items"][0]["unit_price"] == "20.00"
    assert body["items"][0]["line_total"] == "60.00"


def test_line_total_rounds_half_up_not_bankers(
    client: TestClient, session: Session
) -> None:
    """0.10 x 0.25 is 0.025, which is 0.03 half-up and 0.02 banker's rounding."""
    lead = make_lead(session)

    body = create_quotation(client, lead.id, items=[item("Fraction", "0.10", "0.25")])

    assert body["items"][0]["line_total"] == "0.03"


def test_fractional_quantity_is_allowed(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    body = create_quotation(client, lead.id, items=[item("Hours", "2.5", "40.00")])

    assert body["items"][0]["line_total"] == "100.00"


def test_unit_price_of_zero_is_allowed(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    body = create_quotation(client, lead.id, items=[item("Courtesy call", "1", "0")])

    assert body["items"][0]["line_total"] == "0.00"
    assert body["subtotal"] == "0.00"


# ---------------------------------------------------------------------------
# Rejections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("quantity", ["0", "-1", "-0.01"])
def test_invalid_quantity_is_rejected(
    client: TestClient, session: Session, quantity: str
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations",
        json=payload(items=[item(quantity=quantity)]),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("unit_price", ["-0.01", "-100"])
def test_negative_unit_price_is_rejected(
    client: TestClient, session: Session, unit_price: str
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations",
        json=payload(items=[item(unit_price=unit_price)]),
    )

    assert response.status_code == 422


def test_negative_discount_is_rejected(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations", json=payload(discount="-10.00")
    )

    assert response.status_code == 422


def test_discount_greater_than_subtotal_is_rejected(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations", json=payload(discount="300.01")
    )

    assert response.status_code == 422
    assert "subtotal" in response.json()["detail"]


def test_empty_quotation_is_rejected(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/quotations", json=payload(items=[]))

    assert response.status_code == 422


def test_quotation_without_items_key_is_rejected(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.post(f"/api/leads/{lead.id}/quotations", json={"currency": "GBP"})

    assert response.status_code == 422


@pytest.mark.parametrize("description", ["", "   ", "\n"])
def test_blank_item_description_is_rejected(
    client: TestClient, session: Session, description: str
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations",
        json=payload(items=[item(description=description)]),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("currency", ["gbp", "GBPX", "G", "POUNDS"])
def test_invalid_currency_code_is_rejected(
    client: TestClient, session: Session, currency: str
) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations", json=payload(currency=currency)
    )

    assert response.status_code == 422


@pytest.mark.parametrize("unit_price", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_amount_is_rejected(
    client: TestClient, session: Session, unit_price: str
) -> None:
    """A non-finite value would otherwise poison every total it touched.

    Sent as a JSON string because a bare NaN literal is not valid JSON and is
    refused by the HTTP client before it ever reaches the API.
    """
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations",
        json=payload(items=[item(unit_price=unit_price)]),
    )

    assert response.status_code == 422


def test_non_finite_discount_is_rejected(client: TestClient, session: Session) -> None:
    lead = make_lead(session)

    response = client.post(
        f"/api/leads/{lead.id}/quotations", json=payload(discount="NaN")
    )

    assert response.status_code == 422


def test_quotation_for_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.post("/api/leads/999999/quotations", json=payload())

    assert response.status_code == 404
    assert response.json() == {"detail": "Lead 999999 not found"}


# ---------------------------------------------------------------------------
# Retrieval and history
# ---------------------------------------------------------------------------


def test_get_quotation_by_id(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)

    response = client.get(f"/api/quotations/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_quotation_returns_404(client: TestClient) -> None:
    response = client.get("/api/quotations/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Quotation 999999 not found"}


def test_list_quotations_for_lead_returns_empty(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)

    response = client.get(f"/api/leads/{lead.id}/quotations")

    assert response.status_code == 200
    assert response.json() == []


def test_quotations_for_unknown_lead_returns_404(client: TestClient) -> None:
    response = client.get("/api/leads/999999/quotations")

    assert response.status_code == 404


def test_a_lead_can_have_multiple_quotations(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    first = create_quotation(client, lead.id, items=[item("Version one", "1", "100.00")])
    second = create_quotation(client, lead.id, items=[item("Version two", "1", "120.00")])

    response = client.get(f"/api/leads/{lead.id}/quotations")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    # Newest first.
    assert [q["id"] for q in body] == [second["id"], first["id"]]
    assert [q["items"][0]["description"] for q in body] == ["Version two", "Version one"]


def test_quotations_are_scoped_to_their_own_lead(
    client: TestClient, session: Session
) -> None:
    first = make_lead(session, "Sarah Johnson")
    second = make_lead(session, "Daniel Okoro")
    create_quotation(client, first.id)
    create_quotation(client, second.id)
    create_quotation(client, second.id)

    assert len(client.get(f"/api/leads/{first.id}/quotations").json()) == 1
    assert len(client.get(f"/api/leads/{second.id}/quotations").json()) == 2


def test_deleting_items_on_edit_does_not_leave_orphans(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    created = create_quotation(
        client, lead.id, items=[item("One", "1", "10.00"), item("Two", "1", "20.00")]
    )
    assert created and len(created["items"]) == 2

    response = client.post(
        f"/api/quotations/{created['id']}/update",
        json=payload(items=[item("Only one now", "1", "30.00")]),
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    session.expire_all()
    assert session.query(QuotationItem).count() == 1


# ---------------------------------------------------------------------------
# Draft editing
# ---------------------------------------------------------------------------


def test_draft_can_be_edited(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)

    response = client.post(
        f"/api/quotations/{created['id']}/update",
        json=payload(
            items=[item("Revised scope", "3", "100.00")], discount="25.00"
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["description"] == "Revised scope"
    assert body["subtotal"] == "300.00"
    assert body["total"] == "275.00"
    # Editing a draft does not move it along the lifecycle.
    assert body["status"] == "DRAFT"


def test_editing_a_draft_updates_the_lead_row(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)

    client.post(
        f"/api/quotations/{created['id']}/update",
        json=payload(currency="NGN", notes="New terms"),
    )

    assert client.get(f"/api/leads/{lead.id}/quotations").json()[0]["currency"] == "NGN"


def test_edit_rejects_an_empty_quotation(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)

    response = client.post(
        f"/api/quotations/{created['id']}/update", json=payload(items=[])
    )

    assert response.status_code == 422


def test_update_unknown_quotation_returns_404(client: TestClient) -> None:
    response = client.post("/api/quotations/999999/update", json=payload())

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def test_draft_to_sent(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)

    response = client.post(
        f"/api/quotations/{created['id']}/status", json={"status": "SENT"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SENT"
    assert body["sent_at"] is not None


def test_sent_to_accepted(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)
    client.post(f"/api/quotations/{created['id']}/status", json={"status": "SENT"})

    response = client.post(
        f"/api/quotations/{created['id']}/status", json={"status": "ACCEPTED"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"


def test_sent_to_rejected(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)
    client.post(f"/api/quotations/{created['id']}/status", json={"status": "SENT"})

    response = client.post(
        f"/api/quotations/{created['id']}/status", json={"status": "REJECTED"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


@pytest.mark.parametrize(
    ("start", "target"),
    [
        ("DRAFT", "ACCEPTED"),
        ("DRAFT", "REJECTED"),
        ("SENT", "DRAFT"),
        ("ACCEPTED", "SENT"),
        ("ACCEPTED", "REJECTED"),
        ("REJECTED", "ACCEPTED"),
    ],
)
def test_invalid_transitions_are_rejected(
    client: TestClient, session: Session, start: str, target: str
) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)

    if start != "DRAFT":
        client.post(f"/api/quotations/{created['id']}/status", json={"status": "SENT"})
    if start in ("ACCEPTED", "REJECTED"):
        client.post(
            f"/api/quotations/{created['id']}/status", json={"status": start}
        )

    response = client.post(
        f"/api/quotations/{created['id']}/status", json={"status": target}
    )

    assert response.status_code == 409


def test_same_status_transition_is_rejected(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)

    response = client.post(
        f"/api/quotations/{created['id']}/status", json={"status": "DRAFT"}
    )

    assert response.status_code == 409


def test_unknown_status_is_rejected(client: TestClient, session: Session) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)

    response = client.post(
        f"/api/quotations/{created['id']}/status", json={"status": "CANCELLED"}
    )

    assert response.status_code == 422


def test_transition_unknown_quotation_returns_404(client: TestClient) -> None:
    response = client.post("/api/quotations/999999/status", json={"status": "SENT"})

    assert response.status_code == 404


@pytest.mark.parametrize("sent_state", ["SENT", "ACCEPTED", "REJECTED"])
def test_sent_quotation_cannot_be_edited(
    client: TestClient, session: Session, sent_state: str
) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)
    client.post(f"/api/quotations/{created['id']}/status", json={"status": "SENT"})
    if sent_state != "SENT":
        client.post(
            f"/api/quotations/{created['id']}/status", json={"status": sent_state}
        )

    response = client.post(
        f"/api/quotations/{created['id']}/update",
        json=payload(items=[item("Sneaky change", "99", "1.00")]),
    )

    assert response.status_code == 409
    # The stored quotation is untouched.
    assert client.get(f"/api/quotations/{created['id']}").json()["items"][0][
        "description"
    ] == "Deep clean"


# ---------------------------------------------------------------------------
# Lead status integration
# ---------------------------------------------------------------------------


def test_sending_a_quotation_sets_the_lead_to_quote_sent(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    client.post(f"/api/leads/{lead.id}/status", json={"status": "QUALIFIED"})
    created = create_quotation(client, lead.id)

    client.post(f"/api/quotations/{created['id']}/status", json={"status": "SENT"})

    assert client.get(f"/api/leads/{lead.id}").json()["status"] == "QUOTE_SENT"


def test_sending_does_not_stamp_sent_at_twice(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    first = create_quotation(client, lead.id)
    client.post(f"/api/quotations/{first['id']}/status", json={"status": "SENT"})

    second = create_quotation(client, lead.id)
    client.post(f"/api/quotations/{second['id']}/status", json={"status": "SENT"})

    # Each quotation keeps its own send timestamp.
    assert first["sent_at"] is None
    assert client.get(f"/api/quotations/{second['id']}").json()["sent_at"] is not None


@pytest.mark.parametrize("outcome", ["ACCEPTED", "REJECTED"])
def test_accepting_or_rejecting_does_not_change_the_lead_status(
    client: TestClient, session: Session, outcome: str
) -> None:
    """Staff keep control of the pipeline: a decided quote is not a closed lead."""
    lead = make_lead(session)
    client.post(f"/api/leads/{lead.id}/status", json={"status": "QUALIFIED"})
    created = create_quotation(client, lead.id)
    client.post(f"/api/quotations/{created['id']}/status", json={"status": "SENT"})

    client.post(f"/api/quotations/{created['id']}/status", json={"status": outcome})

    lead_after = client.get(f"/api/leads/{lead.id}").json()
    assert lead_after["status"] == "QUOTE_SENT"
    assert lead_after["status"] not in ("WON", "LOST")


def test_staff_can_still_close_the_lead_afterwards(
    client: TestClient, session: Session
) -> None:
    lead = make_lead(session)
    created = create_quotation(client, lead.id)
    client.post(f"/api/quotations/{created['id']}/status", json={"status": "SENT"})
    client.post(f"/api/quotations/{created['id']}/status", json={"status": "ACCEPTED"})

    response = client.post(f"/api/leads/{lead.id}/status", json={"status": "WON"})

    assert response.status_code == 200
    assert response.json()["status"] == "WON"
