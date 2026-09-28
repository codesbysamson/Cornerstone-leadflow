from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    service: Mapped[str] = mapped_column(String(100), nullable=False)
    property_type: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)

    property_size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="NEW", server_default="NEW"
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="WEBSITE", server_default="WEBSITE"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    # The next action staff owe this lead. Stored on the lead rather than in a
    # table because the invariant is at most one current follow-up: it is
    # overwritten on reschedule and nulled on clear. The append-only record of
    # what actually happened belongs in LeadNote instead.
    next_follow_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_follow_up_action: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )


class LeadNote(Base):
    """A staff note or activity against a lead.

    Separate from Lead for three reasons: a lead accumulates an unbounded
    number of them; they are written far less often than leads are read, so
    keeping them out of the row stops note writes from turning into updates on
    a row that every lead-list load touches; and they are append-only and
    newest-first, which is a different lifecycle from the mutable follow-up
    state above.

    There is deliberately no author column. Authentication and users are out of
    scope for this milestone, so a note records what happened and when, not who
    did it. See the milestone risk notes.
    """

    __tablename__ = "lead_notes"

    id: Mapped[int] = mapped_column(primary_key=True)

    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
