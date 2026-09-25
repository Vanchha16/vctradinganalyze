"""add fetched_at to price_candles

Revision ID: b2d6f0a8c914
Revises: e7a4c19b3d52
Create Date: 2026-09-25 11:00:00.000000

ADR-183 follow-up (audit D9). The collector stores the forming candle and
rewrites it in place, so a candle whose period has ended can still hold the
values it had while forming. `fetched_at` records when the request that last
wrote a row was made, so a reader can tell a closed candle from a final one.

One nullable column, no default and no backfill: rows written before it
existed stay null, and nothing else changes.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2d6f0a8c914"
down_revision: str | Sequence[str] | None = "e7a4c19b3d52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "price_candles", sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("price_candles", "fetched_at")
