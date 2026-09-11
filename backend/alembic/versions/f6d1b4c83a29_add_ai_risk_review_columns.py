"""add ai risk review columns

Revision ID: f6d1b4c83a29
Revises: e5c9a3b27d18
Create Date: 2026-09-11 19:30:00.000000

ADR-167: the AI risk manager's verdict on BUY/SELL analyses. All nullable -
WAIT analyses, and every analysis before this, have no review.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6d1b4c83a29"
down_revision: str | Sequence[str] | None = "e5c9a3b27d18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "risk_review_verdict",
    "risk_review_mode",
    "risk_review_reasons",
    "risk_review_key_risk",
    "risk_review_model",
    "risk_review_input_tokens",
    "risk_review_output_tokens",
)


def upgrade() -> None:
    columns = [
        sa.Column("risk_review_verdict", sa.String(length=10), nullable=True),
        sa.Column("risk_review_mode", sa.String(length=10), nullable=True),
        sa.Column("risk_review_reasons", sa.JSON(), nullable=True),
        sa.Column("risk_review_key_risk", sa.String(length=400), nullable=True),
        sa.Column("risk_review_model", sa.String(length=100), nullable=True),
        sa.Column("risk_review_input_tokens", sa.Integer(), nullable=True),
        sa.Column("risk_review_output_tokens", sa.Integer(), nullable=True),
    ]
    for column in columns:
        op.add_column("ai_analysis", column)


def downgrade() -> None:
    # Batch mode so the downgrade also works on the SQLite verification DB.
    with op.batch_alter_table("ai_analysis") as batch:
        for column in reversed(_COLUMNS):
            batch.drop_column(column)
