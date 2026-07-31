"""create smc tables

Revision ID: 6ecc6c49e631
Revises: bf6440f525a1
Create Date: 2026-07-31 14:06:27.274228

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6ecc6c49e631"
down_revision: str | Sequence[str] | None = "bf6440f525a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "smc_events",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "timeframe",
            sa.Enum(
                "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN", name="candle_timeframe"
            ),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.Enum(
                "SWING_HH",
                "SWING_HL",
                "SWING_LH",
                "SWING_LL",
                "BOS",
                "CHOCH",
                "ORDER_BLOCK_BULLISH",
                "ORDER_BLOCK_BEARISH",
                "FAIR_VALUE_GAP_BULLISH",
                "FAIR_VALUE_GAP_BEARISH",
                "LIQUIDITY_EQUAL_HIGHS",
                "LIQUIDITY_EQUAL_LOWS",
                "LIQUIDITY_SWEEP",
                name="smc_event_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "MITIGATED", "INVALIDATED", "ARCHIVED", name="smc_event_status"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("strength", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_smc_events_asset_id"), "smc_events", ["asset_id"], unique=False)
    op.create_index(
        "ix_smc_events_asset_timeframe_type_status",
        "smc_events",
        ["asset_id", "timeframe", "event_type", "status"],
        unique=False,
    )
    op.create_table(
        "smc_processing_states",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column(
            "timeframe",
            sa.Enum(
                "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN", name="candle_timeframe"
            ),
            nullable=False,
        ),
        sa.Column("last_processed_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("engine_version", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id", "timeframe", name="uq_smc_processing_state_asset_timeframe"
        ),
    )
    op.create_index(
        op.f("ix_smc_processing_states_asset_id"),
        "smc_processing_states",
        ["asset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_smc_processing_states_asset_id"), table_name="smc_processing_states")
    op.drop_table("smc_processing_states")
    op.drop_index("ix_smc_events_asset_timeframe_type_status", table_name="smc_events")
    op.drop_index(op.f("ix_smc_events_asset_id"), table_name="smc_events")
    op.drop_table("smc_events")
