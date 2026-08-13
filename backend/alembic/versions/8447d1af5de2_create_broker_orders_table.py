"""create broker_orders table

Revision ID: 8447d1af5de2
Revises: 33eb66dc1919
Create Date: 2026-08-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8447d1af5de2"
down_revision: str | Sequence[str] | None = "33eb66dc1919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "broker_orders",
        sa.Column("signal_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("broker_order_id", sa.String(length=64), nullable=True),
        sa.Column("broker_position_id", sa.String(length=64), nullable=True),
        sa.Column("broker_deal_id", sa.String(length=64), nullable=True),
        sa.Column("volume", sa.Numeric(20, 8), nullable=False),
        sa.Column("requested_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("filled_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(20, 8), nullable=False),
        sa.Column("take_profit", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "FILLED", "CANCELLED", "REJECTED", "CLOSED", name="order_status"),
            nullable=False,
        ),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # A single unique index, not a separate UniqueConstraint + non-unique
    # index - matches the model's `unique=True, index=True` on
    # `signal_id` exactly (the drift pattern `33eb66dc1919` had to fix
    # for `telegram_accounts` after getting this wrong the first time -
    # not repeating it here).
    op.create_index(op.f("ix_broker_orders_signal_id"), "broker_orders", ["signal_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_broker_orders_signal_id"), table_name="broker_orders")
    op.drop_table("broker_orders")
