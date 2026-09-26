from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr


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
