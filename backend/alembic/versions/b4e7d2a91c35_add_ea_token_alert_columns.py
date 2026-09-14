"""add ea token alert columns

Revision ID: b4e7d2a91c35
Revises: f6d1b4c83a29
Create Date: 2026-09-14 03:00:00.000000

ADR-170: what an EA 1.30 reports about its daily loss limit, and which Telegram
alerts about the terminal were already sent. All nullable - an older EA reports
none of it, and no alert has been sent for any existing token.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b4e7d2a91c35"
down_revision: str | Sequence[str] | None = "f6d1b4c83a29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "ea_currency",
    "ea_daily_loss_limit",
    "ea_daily_loss",
    "effective_loss_blocked",
    "offline_alerted_at",
    "loss_limit_alerted_at",
)


def upgrade() -> None:
    columns = [
        sa.Column("ea_currency", sa.String(length=8), nullable=True),
        sa.Column("ea_daily_loss_limit", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("ea_daily_loss", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("effective_loss_blocked", sa.Boolean(), nullable=True),
        sa.Column("offline_alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("loss_limit_alerted_at", sa.DateTime(timezone=True), nullable=True),
    ]
    for column in columns:
        op.add_column("ea_tokens", column)


def downgrade() -> None:
    # Batch mode so the downgrade also works on the SQLite verification DB.
    with op.batch_alter_table("ea_tokens") as batch:
        for column in reversed(_COLUMNS):
            batch.drop_column(column)
