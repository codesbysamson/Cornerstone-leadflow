"""add lead notes and next follow-up

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-28

Additive only: three nullable/enumerable additions and one new table. Existing
rows remain valid and no data is rewritten, so this is safe to apply against a
populated Milestone 4A database.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The next action staff owe this lead. Nullable so existing leads stay
    # valid and a lead with no follow-up set needs no sentinel value.
    op.add_column(
        "leads",
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("next_follow_up_action", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "lead_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # CASCADE so notes can never outlive their lead.
        sa.ForeignKeyConstraint(
            ["lead_id"], ["leads.id"], ondelete="CASCADE", name="fk_lead_notes_lead"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Every note lookup filters on lead_id, so the index is always used.
    op.create_index(
        op.f("ix_lead_notes_lead_id"), "lead_notes", ["lead_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lead_notes_lead_id"), table_name="lead_notes")
    op.drop_table("lead_notes")
    op.drop_column("leads", "next_follow_up_action")
    op.drop_column("leads", "next_follow_up_at")
