"""create staff authentication tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-29

Three new tables. Nothing existing is altered, so Milestone 1-5 data (leads,
notes, follow-ups, quotations and their items) is untouched and remains valid.

No secret is stored in this migration. The first staff account is created by
`python -m app.cli create-staff`, never by a seeding migration, so no credential
hash is baked into a file that would then live in git history permanently.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staff_users",
        sa.Column("id", sa.Integer(), nullable=False),
        # Lowercased on write, so uniqueness cannot be bypassed by case alone.
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        # An Argon2id PHC string. The plaintext password is never stored and is
        # not recoverable from this column.
        sa.Column("password_hash", sa.Text(), nullable=False),
        # Lets an account be disabled instantly without deleting it.
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        # One account per address.
        sa.UniqueConstraint("email", name="uq_staff_users_email"),
    )

    op.create_table(
        "staff_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("staff_user_id", sa.Integer(), nullable=False),
        # Hex SHA-256 of the cookie value. The raw token exists only in the
        # HttpOnly cookie and is never persisted, so a database dump or an SQL
        # injection yields nothing replayable.
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        # The CSRF token is also stored only as a digest, for the same reason.
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        # CASCADE: deleting a staff account must not leave live sessions behind.
        sa.ForeignKeyConstraint(
            ["staff_user_id"],
            ["staff_users.id"],
            ondelete="CASCADE",
            name="fk_staff_sessions_staff_user",
        ),
        # Sessions are looked up by this digest on every authenticated request.
        sa.UniqueConstraint("token_hash", name="uq_staff_sessions_token_hash"),
    )
    op.create_index(
        "ix_staff_sessions_staff_user_id",
        "staff_sessions",
        ["staff_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_staff_sessions_expires_at", "staff_sessions", ["expires_at"], unique=False
    )

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        # A digest of the lowercased email in a private namespace, not the
        # address itself, so this table cannot become a list of probed accounts.
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_login_attempts_key"),
    )


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_index("ix_staff_sessions_expires_at", table_name="staff_sessions")
    op.drop_index("ix_staff_sessions_staff_user_id", table_name="staff_sessions")
    op.drop_table("staff_sessions")
    op.drop_table("staff_users")
