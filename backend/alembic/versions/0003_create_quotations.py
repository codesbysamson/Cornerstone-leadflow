"""create quotations and quotation items

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-28

Two new tables only. Nothing existing is altered, so Milestone 4B data (leads,
notes and follow-ups) is untouched and remains valid.

Every monetary column is NUMERIC(12, 2) — exact decimal storage, never float.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(precision=12, scale=2)


def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False),
        # ISO 4217 alphabetic code so a deployment can quote in NGN or USD with
        # no schema change. Symbol formatting happens at display time.
        sa.Column("currency", sa.String(length=3), server_default="GBP", nullable=False),
        sa.Column("subtotal", MONEY, nullable=False),
        sa.Column("discount", MONEY, server_default="0", nullable=False),
        sa.Column("total", MONEY, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        # CASCADE: a quotation is meaningless without its lead.
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            ondelete="CASCADE",
            name="fk_quotations_lead",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_quotations_lead_id"), "quotations", ["lead_id"], unique=False
    )

    op.create_table(
        "quotation_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quotation_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        # Decimal rather than integer so a quote can bill fractional hours.
        sa.Column("quantity", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("line_total", MONEY, nullable=False),
        # CASCADE: replacing a draft's items must never leave orphans behind.
        sa.ForeignKeyConstraint(
            ["quotation_id"],
            ["quotations.id"],
            ondelete="CASCADE",
            name="fk_quotation_items_quotation",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_quotation_items_quotation_id"),
        "quotation_items",
        ["quotation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_quotation_items_quotation_id"), table_name="quotation_items")
    op.drop_table("quotation_items")
    op.drop_index(op.f("ix_quotations_lead_id"), table_name="quotations")
    op.drop_table("quotations")
