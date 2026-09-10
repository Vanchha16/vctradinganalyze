"""drop tradingview_alerts

Revision ID: a7c4e2b91d38
Revises: f3d81a05c74e
Create Date: 2026-09-10 00:00:00.000000

ADR-154 (extending ADR-142/143's precedent): the TradingView webhook
receiver is removed, so its table goes with it.

The feature was built (ADR-146) but never switched on -
`TRADINGVIEW_WEBHOOK_SECRET` was never set in production, so the route
fail-closed to 404 and the table ended its life with zero rows. Nothing
is lost by dropping it.

`downgrade()` recreates the table but NOT the code that fed it; use
`d5a2f61c983b`'s definition as the reference if the feature is ever
revived.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7c4e2b91d38"
down_revision: str | Sequence[str] | None = "f3d81a05c74e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_tradingview_alerts_created_at"), table_name="tradingview_alerts")
    op.drop_index(op.f("ix_tradingview_alerts_symbol"), table_name="tradingview_alerts")
    op.drop_table("tradingview_alerts")


def downgrade() -> None:
    """Copied verbatim from `d5a2f61c983b` so a downgrade restores the
    exact original shape - not a from-memory reconstruction."""
    op.create_table(
        "tradingview_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("alert_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tradingview_alerts_symbol"), "tradingview_alerts", ["symbol"], unique=False
    )
    op.create_index(
        op.f("ix_tradingview_alerts_created_at"),
        "tradingview_alerts",
        ["created_at"],
        unique=False,
    )
