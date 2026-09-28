from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    field_validator,
)

MAX_NOTE_LENGTH = 2000
MAX_FOLLOW_UP_ACTION_LENGTH = 255
MAX_QUOTATION_NOTES_LENGTH = 4000
MAX_ITEM_DESCRIPTION_LENGTH = 500

#: A quoted amount must be a real ISO 4217 alphabetic code. Any three-letter
#: code is accepted so another deployment can quote in NGN or USD without a
#: code change; formatting falls back gracefully if a code is unrecognised.
CURRENCY_PATTERN = r"^[A-Z]{3}$"
DEFAULT_CURRENCY = "GBP"


class LeadStatus(StrEnum):
    """The CRM pipeline.

    Used for request validation only. The ``leads.status`` column deliberately
    stays a plain ``VARCHAR(50)`` so introducing this set of values requires
    no database migration.
    """

    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    QUOTE_SENT = "QUOTE_SENT"
    WON = "WON"
    LOST = "LOST"


class LeadStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: LeadStatus


class LeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_name: str
    email: EmailStr
    phone: str
    service: str
    property_type: str
    location: str
    property_size: str | None = None
    frequency: str | None = None
    preferred_date: date | None = None
    requirements: str | None = None


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    email: str
    phone: str
    service: str
    property_type: str
    location: str
    property_size: str | None
    frequency: str | None
    preferred_date: date | None
    requirements: str | None
    status: str
    source: str
    created_at: datetime
    # Defaults keep every existing caller and test constructing LeadRead
    # without change. Exposing them here means the dashboard and the lead list
    # get follow-up data from the single existing GET /api/leads call.
    next_follow_up_at: datetime | None = None
    next_follow_up_action: str | None = None


def _require_aware(value: datetime) -> datetime:
    """Reject a datetime that carries no timezone offset.

    A ``datetime-local`` control yields a naive value, and PostgreSQL would
    silently interpret a naive timestamp in the *server's* zone when it is
    written to a ``timestamptz`` column. That fails quietly and corrupts the
    stored instant, so the API refuses it and forces the caller to be explicit.
    """
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(
            "due_at must include a timezone offset, for example "
            "2026-10-05T14:30:00Z or 2026-10-05T14:30:00+01:00"
        )
    return value


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: Annotated[str, Field(min_length=1, max_length=MAX_NOTE_LENGTH)]

    @field_validator("body")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        # min_length alone lets "   " through, which would store an
        # invisible note in the activity history.
        if not value.strip():
            raise ValueError("Note cannot be blank")
        return value


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    body: str
    created_at: datetime


class FollowUpSet(BaseModel):
    """Set or reschedule the next follow-up.

    Reschedule is a plain overwrite of the same two lead columns, so it needs
    no separate endpoint or command.
    """

    model_config = ConfigDict(extra="forbid")

    due_at: datetime
    action: Annotated[str, Field(min_length=1, max_length=MAX_FOLLOW_UP_ACTION_LENGTH)]

    _aware_due_at = field_validator("due_at")(_require_aware)

    @field_validator("action")
    @classmethod
    def reject_blank_action(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Follow-up action cannot be blank")
        return value


class FollowUpClear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clear: Literal[True]


class QuotationStatus(StrEnum):
    """The quotation lifecycle.

    Mirrors the LeadStatus convention: request validation only, while the
    ``quotations.status`` column stays a plain VARCHAR(32).
    """

    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class QuotationItemIn(BaseModel):
    """A line as submitted by the browser.

    Deliberately accepts no ``line_total``. Totals are the server's to compute,
    and rejecting the field outright means a client cannot even attempt to
    assert one.
    """

    model_config = ConfigDict(extra="forbid")

    description: Annotated[
        str, Field(min_length=1, max_length=MAX_ITEM_DESCRIPTION_LENGTH)
    ]
    quantity: Decimal
    unit_price: Decimal

    @field_validator("description")
    @classmethod
    def reject_blank_description(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Item description cannot be blank")
        return value.strip()


class QuotationWrite(BaseModel):
    """Create or replace the editable content of a quotation."""

    model_config = ConfigDict(extra="forbid")

    currency: Annotated[str, Field(pattern=CURRENCY_PATTERN)] = DEFAULT_CURRENCY
    discount: Decimal = Decimal("0.00")
    notes: Annotated[str | None, Field(max_length=MAX_QUOTATION_NOTES_LENGTH)] = None
    # A quotation with no billable lines is not a quotation.
    items: Annotated[list[QuotationItemIn], Field(min_length=1)]

    @field_validator("notes")
    @classmethod
    def normalise_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class QuotationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: QuotationStatus


class QuotationItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class QuotationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    status: str
    currency: str
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None
    items: list[QuotationItemRead]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reference(self) -> str:
        """Human-facing reference, e.g. Q-0001.

        Derived from the id so it needs no column, no uniqueness constraint and
        no sequence to keep in step.
        """
        return f"Q-{self.id:04d}"
