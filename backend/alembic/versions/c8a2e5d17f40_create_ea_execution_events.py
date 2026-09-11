"""create ea_execution_events

Revision ID: c8a2e5d17f40
Revises: b3f9d27c61e5
Create Date: 2026-09-11 13:30:00.000000

ADR-162: what an MT5 Expert Advisor reports it did with each signal.
Written by hand, like b3f9d27c61e5, so autogenerate's spurious
`uq_telegram_accounts_*` drops cannot creep in.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8a2e5d17f40"
down_revision: str | Sequence[str] | None = "b3f9d27c61e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ea_execution_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_id", sa.Uuid(), nullable=True),
        sa.Column("token_name", sa.String(length=64), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_login", sa.String(length=32), nullable=False),
        sa.Column("broker_symbol", sa.String(length=32), nullable=False),
        sa.Column("order_type", sa.String(length=32), nullable=True),
        sa.Column("order_ticket", sa.BigInteger(), nullable=True),
        sa.Column("position_id", sa.BigInteger(), nullable=True),
        sa.Column("volume", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("take_profit", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("profit", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("retcode", sa.Integer(), nullable=True),
        sa.Column("close_reason", sa.String(length=16), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        # SET NULL: revoking a terminal's token must not erase what it did.
        sa.ForeignKeyConstraint(["token_id"], ["ea_tokens.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ea_execution_events_user_event_key",
        "ea_execution_events",
        ["user_id", "event_key"],
        unique=True,
    )
    op.create_index(
        "ix_ea_execution_events_user_occurred",
        "ea_execution_events",
        ["user_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ea_execution_events_signal_id"),
        "ea_execution_events",
        ["signal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ea_execution_events_signal_id"), table_name="ea_execution_events")
    op.drop_index("ix_ea_execution_events_user_occurred", table_name="ea_execution_events")
    op.drop_index("ix_ea_execution_events_user_event_key", table_name="ea_execution_events")
    op.drop_table("ea_execution_events")
