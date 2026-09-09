"""add signals.strategy

Revision ID: e91b47c26fa8
Revises: d5a2f61c983b
Create Date: 2026-09-09 00:00:00.000000

ADR-147: record which strategy produced each signal, so a delivered
signal can say how it was analysed. `StrategyEngine` has ranked a
`primary_strategy` for every analysis since Phase 5D; the value was
simply never carried through to the `Signal` row.

A plain `String(32)`, not a native enum: BBMA is planned as a seventh
strategy (docs/61) and adding one must not require an enum migration.
Nullable - existing rows have no recorded strategy, and an analysis
where every strategy was rejected legitimately has none.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e91b47c26fa8"
down_revision: str | Sequence[str] | None = "d5a2f61c983b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `batch_alter_table` per BACKLOG §26: any column added to an existing
    # table must use batch mode for SQLite compatibility. No-op on Postgres.
    with op.batch_alter_table("signals") as batch_op:
        batch_op.add_column(sa.Column("strategy", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("signals") as batch_op:
        batch_op.drop_column("strategy")
