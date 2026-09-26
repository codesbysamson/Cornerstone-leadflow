from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr


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
