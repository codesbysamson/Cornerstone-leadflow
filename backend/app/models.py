from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

#: All persisted money is NUMERIC(12, 2) and handled as Decimal. Never float.
MONEY_TYPE = Numeric(12, 2)
QUANTITY_TYPE = Numeric(12, 2)


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


class Quotation(Base):
    """A commercial quote issued to a lead.

    A lead may accumulate several quotations over its life, so this is a real
    one-to-many relationship rather than columns on the lead. Items live in
    their own table for the same reason: they are queried, constrained and
    cascade-deleted independently, and embedding them as JSON on the lead would
    make them impossible to index or validate at the database level.

    ``subtotal``, ``discount`` and ``total`` are stored rather than derived on
    read so that the figures a customer was shown remain fixed for the life of
    the quotation, even if the pricing rules change later.
    """

    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(primary_key=True)

    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # A plain VARCHAR, matching how leads.status is handled: adding a status
    # later must not require a migration.
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT", server_default="DRAFT"
    )

    # Stored as an ISO 4217 alphabetic code so another deployment can quote in
    # NGN or USD with no code change. Symbol formatting is a display concern.
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="GBP", server_default="GBP"
    )

    subtotal: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    discount: Mapped[Decimal] = mapped_column(
        MONEY_TYPE, nullable=False, default=Decimal("0.00"), server_default="0"
    )
    total: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    # Set when the quotation is first sent, and left alone afterwards.
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # delete-orphan so replacing a draft's items cannot leave orphans behind,
    # and selectin so the items are available for serialisation without a lazy
    # load that could fail after the session closes.
    items: Mapped[list["QuotationItem"]] = relationship(
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="QuotationItem.id",
        lazy="selectin",
    )


class QuotationItem(Base):
    """A single billed line on a quotation.

    ``line_total`` is denormalised deliberately: it is the authoritative figure
    for that line, and recomputing it at read time would let a change to the
    pricing rule silently rewrite the arithmetic of a quotation a customer has
    already accepted.
    """

    __tablename__ = "quotation_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(String(500), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(QUANTITY_TYPE, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(MONEY_TYPE, nullable=False)

    quotation: Mapped[Quotation] = relationship(back_populates="items")
