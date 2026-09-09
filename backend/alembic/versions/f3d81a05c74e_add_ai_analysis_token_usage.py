"""add ai_analysis token usage

Revision ID: f3d81a05c74e
Revises: e91b47c26fa8
Create Date: 2026-09-09 00:00:00.000000

ADR-149: record the provider's reported token usage per analysis.

Until now nothing in this project measured LLM spend - only `latency_ms`
was stored - so any question about cost, or about whether a different
model is worth its price, could only be answered with an estimate.
Nullable and never back-filled: pre-existing analyses have no usage, and
inventing one would defeat the point.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3d81a05c74e"
down_revision: str | Sequence[str] | None = "e91b47c26fa8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table per BACKLOG §26 - SQLite compatibility for a
    # column added to an existing table. No-op on Postgres.
    with op.batch_alter_table("ai_analysis") as batch_op:
        batch_op.add_column(sa.Column("input_tokens", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("output_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ai_analysis") as batch_op:
        batch_op.drop_column("output_tokens")
        batch_op.drop_column("input_tokens")
