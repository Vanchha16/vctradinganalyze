"""create paper_swing_trades

Revision ID: d7c4a9e1f203
Revises: b2d6f0a8c914
Create Date: 2026-09-19 10:00:00.000000

ADR-182: the swing strategy's paper record - every setup, and every paper
trade's outcome. Written by hand, like c8a2e5d17f40, so autogenerate's
spurious `uq_telegram_accounts_*` drops cannot creep in. No data changes:
the three currency assets are created (inactive) by the paper task itself.
Re-attached after b2d6f0a8c914 (ADR-183 D9) when ported onto production
54f2e05 - it was written against b4e7d2a91c35 and nothing in it depends on
the revisions in between.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7c4a9e1f203"
down_revision: str | Sequence[str] | None = "b2d6f0a8c914"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRICE = sa.Numeric(precision=20, scale=8)
_METRIC = sa.Numeric(precision=12, scale=4)


def upgrade() -> None:
    op.create_table(
        "paper_swing_trades",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("setup", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("d1_trend", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reject_reason", sa.String(length=32), nullable=True),
        sa.Column("signal_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pivot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pullback_level", _PRICE, nullable=False),
        sa.Column("entry_price", _PRICE, nullable=False),
        sa.Column("stop_loss", _PRICE, nullable=False),
        sa.Column("take_profit", _PRICE, nullable=False),
        sa.Column("risk_pips", _METRIC, nullable=False),
        sa.Column("reward_pips", _METRIC, nullable=False),
        sa.Column("risk_reward", _METRIC, nullable=False),
        sa.Column("atr_h4_pips", _METRIC, nullable=False),
        sa.Column("adr_pips", _METRIC, nullable=True),
        sa.Column("spread_pips", _METRIC, nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_price", _PRICE, nullable=True),
        sa.Column("swap_pips", _METRIC, nullable=True),
        sa.Column("result_pips", _METRIC, nullable=True),
        sa.Column("result_r", _METRIC, nullable=True),
        sa.Column("holding_hours", _METRIC, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_paper_swing_trades_asset_direction_pivot",
        "paper_swing_trades",
        ["asset_id", "direction", "pivot_time"],
        unique=True,
    )
    op.create_index(
        "ix_paper_swing_trades_signal_time", "paper_swing_trades", ["signal_time"], unique=False
    )
    op.create_index("ix_paper_swing_trades_status", "paper_swing_trades", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_paper_swing_trades_status", table_name="paper_swing_trades")
    op.drop_index("ix_paper_swing_trades_signal_time", table_name="paper_swing_trades")
    op.drop_index("ix_paper_swing_trades_asset_direction_pivot", table_name="paper_swing_trades")
    op.drop_table("paper_swing_trades")
