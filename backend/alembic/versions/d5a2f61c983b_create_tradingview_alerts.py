"""create tradingview_alerts table

Revision ID: d5a2f61c983b
Revises: c8f31d7b40a2
Create Date: 2026-09-09 00:00:00.000000

ADR-146: inbound TradingView webhook alerts. A new table rather than
reusing `signals` - a `Signal` requires a NOT NULL `analysis_id` into
`ai_analysis` plus a stop and target, none of which a TradingView alert
has. Storing one there would mean fabricating an AI analysis for
something that had none.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5a2f61c983b"
down_revision: str | Sequence[str] | None = "c8f31d7b40a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
    # Indexed for the admin list's symbol filter. No unique constraint
    # anywhere: TradingView can and does re-fire an alert, and the record
    # of a duplicate arriving is itself information - deduplicating at
    # write time would silently discard it.
    op.create_index(
        op.f("ix_tradingview_alerts_symbol"), "tradingview_alerts", ["symbol"], unique=False
    )
    op.create_index(
        op.f("ix_tradingview_alerts_created_at"),
        "tradingview_alerts",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tradingview_alerts_created_at"), table_name="tradingview_alerts")
    op.drop_index(op.f("ix_tradingview_alerts_symbol"), table_name="tradingview_alerts")
    op.drop_table("tradingview_alerts")
