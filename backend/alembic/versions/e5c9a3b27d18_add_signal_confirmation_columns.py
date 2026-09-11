"""add signal confirmation columns

Revision ID: e5c9a3b27d18
Revises: d4b7f1a93c26
Create Date: 2026-09-11 18:00:00.000000

ADR-166: a BUY/SELL is saved as DRAFT and published only once M15 confirms
it. Both columns are nullable - every existing signal predates
confirmation, so there is nothing to backfill and no default to invent.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5c9a3b27d18"
down_revision: str | Sequence[str] | None = "d4b7f1a93c26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("signals", sa.Column("status_reason", sa.String(length=160), nullable=True))


def downgrade() -> None:
    # Batch mode so the downgrade also works on the SQLite verification DB.
    with op.batch_alter_table("signals") as batch:
        batch.drop_column("status_reason")
        batch.drop_column("confirmed_at")
