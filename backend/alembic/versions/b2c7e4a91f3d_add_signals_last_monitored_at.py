"""add signals.last_monitored_at

Revision ID: b2c7e4a91f3d
Revises: 8447d1af5de2
Create Date: 2026-09-08 00:00:00.000000

ADR-141: the monitoring watermark. `signal_monitoring_tasks.py` used to
evaluate only `PriceCandleRepository.get_latest(asset, M1)` - a single
candle per tick - while M1 candles are only ingested every
`market_data_min_collection_interval_seconds` (300s, ADR-140). Four of
every five ingested candles were therefore never examined for
entry/SL/TP, and a touch that retraced inside that window was missed
permanently. The fix scans a candle *range* each tick; this column is
how far that scan has already progressed, so the range stays bounded
instead of replaying from `triggered_at` forever.

Nullable with no server default: an existing open signal has a NULL
watermark, which the task reads as "scan from `triggered_at`/
`created_at`" - so the first post-deploy run retroactively resolves
every signal the old single-candle logic missed.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c7e4a91f3d"
down_revision: str | Sequence[str] | None = "8447d1af5de2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `batch_alter_table`, not a plain `op.add_column` - SQLite has no
    # `ALTER TABLE ... ADD CONSTRAINT` and this project's institutional
    # note (BACKLOG §26) requires batch mode for any change to an
    # existing table. A no-op wrapper on Postgres.
    with op.batch_alter_table("signals") as batch_op:
        batch_op.add_column(
            sa.Column("last_monitored_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("signals") as batch_op:
        batch_op.drop_column("last_monitored_at")
