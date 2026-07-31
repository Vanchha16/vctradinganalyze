"""create market data tables

Revision ID: bf6440f525a1
Revises: a7dad339df2e
Create Date: 2026-07-31 10:20:59.538565

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "bf6440f525a1"
down_revision: str | Sequence[str] | None = "a7dad339df2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "market_type",
            sa.Enum("FOREX", "METAL", "CRYPTO", "INDEX", name="market_type"),
            nullable=False,
        ),
        sa.Column("exchange", sa.String(length=100), nullable=True),
        sa.Column("base_currency", sa.String(length=10), nullable=True),
        sa.Column("quote_currency", sa.String(length=10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_symbol"), "assets", ["symbol"], unique=True)
    op.create_table(
        "indicator_results",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "timeframe",
            sa.Enum(
                "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN", name="candle_timeframe"
            ),
            nullable=False,
        ),
        sa.Column("indicator", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_indicator_results_asset_id"), "indicator_results", ["asset_id"], unique=False
    )
    op.create_index(
        "ix_indicator_results_asset_timeframe_indicator",
        "indicator_results",
        ["asset_id", "timeframe", "indicator"],
        unique=False,
    )
    op.create_table(
        "price_candles",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "timeframe",
            sa.Enum(
                "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN", name="candle_timeframe"
            ),
            nullable=False,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id", "timeframe", "timestamp", name="uq_price_candle_asset_timeframe_timestamp"
        ),
    )
    op.create_index(op.f("ix_price_candles_asset_id"), "price_candles", ["asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_price_candles_asset_id"), table_name="price_candles")
    op.drop_table("price_candles")
    op.drop_index("ix_indicator_results_asset_timeframe_indicator", table_name="indicator_results")
    op.drop_index(op.f("ix_indicator_results_asset_id"), table_name="indicator_results")
    op.drop_table("indicator_results")
    op.drop_index(op.f("ix_assets_symbol"), table_name="assets")
    op.drop_table("assets")
