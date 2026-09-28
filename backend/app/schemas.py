from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

MAX_NOTE_LENGTH = 2000
MAX_FOLLOW_UP_ACTION_LENGTH = 255


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
