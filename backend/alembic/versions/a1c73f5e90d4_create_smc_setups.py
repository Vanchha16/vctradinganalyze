"""create smc_setups

Revision ID: a1c73f5e90d4
Revises: b4e7d2a91c35
Create Date: 2026-09-23 09:00:00.000000

ADR-183: the smc-ict-crt-v1 production path's own state. One row per
evaluated CRT setup, including rejected ones with their real reason, and the
memory that lets a restarted worker resume a pending setup instead of
recomputing it. Touches no existing table, so BBMA's data and behaviour are
untouched.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as pg_enum

from alembic import op

revision: str = "a1c73f5e90d4"
down_revision: str | Sequence[str] | None = "b4e7d2a91c35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATES = (
    "no_setup",
    "crt_anchor_confirmed",
    "raid_confirmed",
    "waiting_for_m5_mss",
    "mss_confirmed",
    "entry_zone_confirmed",
    "signal_created",
    "expired",
    "cancelled",
    "traded",
)


def upgrade() -> None:
    bind = op.get_bind()
    postgres = bind.dialect.name == "postgresql"
    # On PostgreSQL the type is created exactly once, here, and the column
    # below only *references* it (`create_type=False`). Letting `create_table`
    # emit its own CREATE TYPE as well is what failed on 2026-09-23:
    # "type smc_setup_state already exists", inside the same transaction.
    # Other dialects (SQLite in tests) have no enum type to pre-create.
    if postgres:
        pg_enum(*_STATES, name="smc_setup_state").create(bind, checkfirst=True)
        state: sa.types.TypeEngine = pg_enum(
            *_STATES, name="smc_setup_state", create_type=False
        )
    else:
        state = sa.Enum(*_STATES, name="smc_setup_state", native_enum=True)
    op.create_table(
        "smc_setups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("anchor_t", sa.DateTime(timezone=True), nullable=False, index=True),
        # server_default so rows inserted outside the ORM still get a state
        # (the Alembic/`server_default` rule in docs/27).
        sa.Column("state", state, nullable=False, server_default="crt_anchor_confirmed"),
        sa.Column("direction", sa.String(length=4), nullable=True),
        sa.Column("crt_high", sa.Numeric(20, 8), nullable=False),
        sa.Column("crt_low", sa.Numeric(20, 8), nullable=False),
        sa.Column("raid_t", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raid_extreme", sa.Numeric(20, 8), nullable=True),
        sa.Column("closed_back_inside", sa.Boolean(), nullable=True),
        sa.Column("key_levels", sa.String(length=400), nullable=True),
        sa.Column("session", sa.String(length=24), nullable=True),
        sa.Column("location", sa.String(length=16), nullable=True),
        sa.Column("equilibrium", sa.Numeric(20, 8), nullable=True),
        sa.Column("mss_t", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mss_level", sa.Numeric(20, 8), nullable=True),
        sa.Column("entry_basis", sa.String(length=16), nullable=True),
        sa.Column("entry", sa.Numeric(20, 8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(20, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(20, 8), nullable=True),
        sa.Column("risk_reward", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("news_status", sa.String(length=32), nullable=False,
                  server_default="NEWS_UNKNOWN"),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("signal_id", sa.Uuid(), sa.ForeignKey("signals.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("transitions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("asset_id", "anchor_t", name="uq_smc_setups_asset_anchor"),
    )


def downgrade() -> None:
    op.drop_table("smc_setups")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        pg_enum(name="smc_setup_state").drop(bind, checkfirst=True)
