"""Quotation workflow: create, edit as a draft, and move through its lifecycle.

The API surface stays on GET and POST so the existing CORS configuration in
main.py does not have to change. Every mutation is a POST against a sub-resource
of the quotation, matching how /status and /follow-up already work on leads.
"""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_staff
from app.models import Lead, Quotation, QuotationItem
from app.money import (
    MoneyError,
    line_total as compute_line_total,
    parse_money,
    parse_quantity,
    sum_money,
)
from app.schemas import (
    QuotationRead,
    QuotationStatus,
    QuotationStatusUpdate,
    QuotationWrite,
)

# Every quotation route is staff-only, so the dependency sits on the router:
# a route added here later is protected by default.
router = APIRouter(
    prefix="/api",
    tags=["quotations"],
    dependencies=[Depends(require_staff)],
)

#: The only permitted moves. A quotation is a document a customer may already
#: be looking at, so it is not editable once it has left the building, and its
#: final two states are terminal.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    QuotationStatus.DRAFT: {QuotationStatus.SENT},
    QuotationStatus.SENT: {QuotationStatus.ACCEPTED, QuotationStatus.REJECTED},
    QuotationStatus.ACCEPTED: set(),
    QuotationStatus.REJECTED: set(),
}

EDITABLE_STATES = {QuotationStatus.DRAFT}


def _require_lead(lead_id: int, db: Session) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )
    return lead


def _require_quotation(quotation_id: int, db: Session) -> Quotation:
    quotation = db.get(Quotation, quotation_id)
    if quotation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quotation {quotation_id} not found",
        )
    return quotation


def _require_editable(quotation: Quotation) -> None:
    if quotation.status not in EDITABLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Quotation {quotation.id} is {quotation.status} and can no "
                "longer be edited. Create a new quotation instead."
            ),
        )


def _price(
    payload: QuotationWrite,
) -> tuple[list[dict], Decimal, Decimal, Decimal]:
    """Computes every money figure for a quotation.

    The browser sends descriptions, quantities and unit prices only. Line
    totals, the subtotal and the final total are derived here, so the stored
    figures cannot be influenced by the client. Any rejection is a 422 because
    the submitted content is what is wrong.

    Returns the priced lines, subtotal, total and discount.
    """
    priced: list[dict] = []

    try:
        for index, item in enumerate(payload.items):
            quantity = parse_quantity(item.quantity)
            unit_price = parse_money(item.unit_price, field="unit price")
            priced.append(
                {
                    "description": item.description,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": compute_line_total(quantity, unit_price),
                }
            )

        subtotal = sum_money([line["line_total"] for line in priced])
        discount = parse_money(payload.discount, field="discount")

        if discount > subtotal:
            raise MoneyError(
                "Discount cannot be greater than the subtotal "
                f"({discount} > {subtotal})"
            )

        total = sum_money([subtotal, -discount])
    except MoneyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return priced, subtotal, total, discount


def _apply_items(quotation: Quotation, priced: list[dict]) -> None:
    """Replaces a draft's items wholesale.

    delete-orphan on the relationship removes the old rows, so replacing the
    list cannot leave orphaned items behind.
    """
    quotation.items = [
        QuotationItem(
            description=line["description"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            line_total=line["line_total"],
        )
        for line in priced
    ]


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


@router.get("/leads/{lead_id}/quotations", response_model=list[QuotationRead])
def list_quotations(lead_id: int, db: Session = Depends(get_db)) -> list[Quotation]:
    """All quotations for a lead, newest first.

    Scoped under the lead so the history screen is a single call, and so an
    unknown lead 404s rather than returning an empty list that looks like
    "this lead has no quotes".
    """
    _require_lead(lead_id, db)

    result = db.execute(
        select(Quotation)
        .where(Quotation.lead_id == lead_id)
        .order_by(Quotation.id.desc())
    )
    return list(result.scalars().all())


@router.get("/quotations/{quotation_id}", response_model=QuotationRead)
def get_quotation(quotation_id: int, db: Session = Depends(get_db)) -> Quotation:
    return _require_quotation(quotation_id, db)


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


@router.post(
    "/leads/{lead_id}/quotations",
    response_model=QuotationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_quotation(
    lead_id: int, payload: QuotationWrite, db: Session = Depends(get_db)
) -> Quotation:
    """Creates a DRAFT quotation for a lead, priced by the server."""
    _require_lead(lead_id, db)

    priced, subtotal, total, discount = _price(payload)

    quotation = Quotation(
        lead_id=lead_id,
        status=QuotationStatus.DRAFT.value,
        currency=payload.currency,
        subtotal=subtotal,
        discount=discount,
        total=total,
        notes=payload.notes,
    )
    _apply_items(quotation, priced)

    db.add(quotation)
    db.commit()
    db.refresh(quotation)
    return quotation


@router.post("/quotations/{quotation_id}/update", response_model=QuotationRead)
def update_quotation(
    quotation_id: int, payload: QuotationWrite, db: Session = Depends(get_db)
) -> Quotation:
    """Replaces a DRAFT quotation's content and reprices it.

    A single POST replacing the whole document keeps the edit atomic: there is
    no window in which a quotation exists with some items repriced and others
    not.
    """
    quotation = _require_quotation(quotation_id, db)
    _require_editable(quotation)

    priced, subtotal, total, discount = _price(payload)

    quotation.currency = payload.currency
    quotation.discount = discount
    quotation.subtotal = subtotal
    quotation.total = total
    quotation.notes = payload.notes
    _apply_items(quotation, priced)

    db.commit()
    db.refresh(quotation)
    return quotation


@router.post("/quotations/{quotation_id}/status", response_model=QuotationRead)
def transition_quotation(
    quotation_id: int, payload: QuotationStatusUpdate, db: Session = Depends(get_db)
) -> Quotation:
    """Moves a quotation to a new status, rejecting anything not on the map.

    Sending a quotation also moves the lead to QUOTE_SENT, because that is the
    one lead transition the business asked to be automatic. Acceptance and
    rejection deliberately leave the lead alone: staff keep control of the
    pipeline, since a won quote may still need scoping before the lead closes.
    """
    quotation = _require_quotation(quotation_id, db)
    target = payload.status

    permitted = ALLOWED_TRANSITIONS.get(QuotationStatus(quotation.status), set())
    if target not in permitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A quotation cannot move from {quotation.status} to "
                f"{target.value}. Allowed: "
                + (", ".join(sorted(s.value for s in permitted)) or "none")
            ),
        )

    quotation.status = target.value

    if target is QuotationStatus.SENT:
        quotation.sent_at = datetime.now(UTC)
        lead = db.get(Lead, quotation.lead_id)
        if lead is not None:
            lead.status = "QUOTE_SENT"

    db.commit()
    db.refresh(quotation)
    return quotation
