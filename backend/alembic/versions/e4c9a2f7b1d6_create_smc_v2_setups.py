"""create smc_v2_setups

Revision ID: e4c9a2f7b1d6
Revises: d7c4a9e1f203
Create Date: 2026-10-09 12:00:00.000000

ADR-185: the smc-ict-crt-v2 design-A state machine's own table. Additive
only - no existing table, column or row is touched, and v1's `smc_setups`
is left exactly as it is. `state` is text, not a PostgreSQL enum type, so
the enum-creation pitfalls of a1c73f5e90d4/c5b81d4a2f07 cannot recur.
Written by hand, like d7c4a9e1f203.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4c9a2f7b1d6"
down_revision: str | Sequence[str] | None = "d7c4a9e1f203"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRICE = sa.Numeric(precision=20, scale=8)


def upgrade() -> None:
    op.create_table(
        "smc_v2_setups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("strategy", sa.String(length=32), nullable=False),
        sa.Column("design", sa.String(length=8), nullable=False),
        sa.Column("anchor_timeframe", sa.String(length=8), nullable=False),
        sa.Column("anchor_t", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raid_t", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=96), nullable=True),
        sa.Column("direction", sa.String(length=4), nullable=False),
        sa.Column("crt_high", _PRICE, nullable=False),
        sa.Column("crt_low", _PRICE, nullable=False),
        sa.Column("raid_extreme", _PRICE, nullable=False),
        sa.Column("closed_back_inside", sa.Boolean(), nullable=False),
        sa.Column("key_levels", sa.String(length=400), nullable=True),
        sa.Column("session", sa.String(length=24), nullable=True),
        sa.Column("location", sa.String(length=16), nullable=True),
        sa.Column("equilibrium", _PRICE, nullable=True),
        sa.Column("mss_t", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mss_level", _PRICE, nullable=True),
        sa.Column("entry_basis", sa.String(length=16), nullable=True),
        sa.Column("entry", _PRICE, nullable=True),
        sa.Column("stop_loss", _PRICE, nullable=True),
        sa.Column("take_profit", _PRICE, nullable=True),
        sa.Column("risk_reward", sa.Float(), nullable=True),
        sa.Column("stop_distance", _PRICE, nullable=True),
        sa.Column("modelled_spread", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("modelled_cost_r", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trading_day", sa.Date(), nullable=True),
        sa.Column("slot_signal_id", sa.Uuid(), nullable=True),
        sa.Column("published_today", sa.Integer(), nullable=True),
        sa.Column("news_status", sa.String(length=32), nullable=False),
        sa.Column("signal_id", sa.Uuid(), nullable=True),
        sa.Column("transitions", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id", "strategy", "design", "anchor_timeframe", "anchor_t",
            name="uq_smc_v2_setups_identity",
        ),
        sa.UniqueConstraint("signal_id", name="uq_smc_v2_setups_signal_id"),
    )
    op.create_index("ix_smc_v2_setups_asset_id", "smc_v2_setups", ["asset_id"], unique=False)
    op.create_index("ix_smc_v2_setups_anchor_t", "smc_v2_setups", ["anchor_t"], unique=False)
    op.create_index("ix_smc_v2_setups_state", "smc_v2_setups", ["state"], unique=False)
    op.create_index("ix_smc_v2_setups_trading_day", "smc_v2_setups", ["trading_day"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_smc_v2_setups_trading_day", table_name="smc_v2_setups")
    op.drop_index("ix_smc_v2_setups_state", table_name="smc_v2_setups")
    op.drop_index("ix_smc_v2_setups_anchor_t", table_name="smc_v2_setups")
    op.drop_index("ix_smc_v2_setups_asset_id", table_name="smc_v2_setups")
    op.drop_table("smc_v2_setups")
