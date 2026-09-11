"""add ea_tokens settings and terminal report

Revision ID: d4b7f1a93c26
Revises: c8a2e5d17f40
Create Date: 2026-09-11 15:00:00.000000

ADR-163: settings the website pushes to each MT5 terminal, and what the
terminal reports back about itself.

Every NOT NULL column carries a `server_default`: production already has an
`ea_tokens` row, and `ADD COLUMN ... NOT NULL` with no default fails on
Postgres for a non-empty table. The defaults use portable forms
(`sa.false()`/`sa.true()` and plain literals) rather than anything
compiled against the SQLite verification DB - see project memory on
dialect-specific `server_default`s.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4b7f1a93c26"
down_revision: str | Sequence[str] | None = "c8a2e5d17f40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REPORT_COLUMNS = (
    "ea_version",
    "ea_max_lot",
    "ea_allow_remote_live",
    "applied_settings_version",
    "effective_dry_run",
    "effective_paused",
)
_SETTINGS_COLUMNS = (
    "paused",
    "dry_run",
    "lot_size",
    "max_open_trades",
    "max_slippage_points",
    "settings_version",
    "settings_updated_at",
)


def upgrade() -> None:
    op.add_column(
        "ea_tokens",
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ea_tokens",
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "ea_tokens",
        sa.Column(
            "lot_size", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.01"
        ),
    )
    op.add_column(
        "ea_tokens",
        sa.Column("max_open_trades", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "ea_tokens",
        sa.Column("max_slippage_points", sa.Integer(), nullable=False, server_default="50"),
    )
    op.add_column(
        "ea_tokens",
        sa.Column("settings_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "ea_tokens",
        sa.Column("settings_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column("ea_tokens", sa.Column("ea_version", sa.String(length=16), nullable=True))
    op.add_column(
        "ea_tokens", sa.Column("ea_max_lot", sa.Numeric(precision=10, scale=2), nullable=True)
    )
    op.add_column("ea_tokens", sa.Column("ea_allow_remote_live", sa.Boolean(), nullable=True))
    op.add_column("ea_tokens", sa.Column("applied_settings_version", sa.Integer(), nullable=True))
    op.add_column("ea_tokens", sa.Column("effective_dry_run", sa.Boolean(), nullable=True))
    op.add_column("ea_tokens", sa.Column("effective_paused", sa.Boolean(), nullable=True))


def downgrade() -> None:
    # Batch mode so the downgrade also works on the SQLite verification DB,
    # which cannot DROP COLUMN in place.
    with op.batch_alter_table("ea_tokens") as batch:
        for column in (*_REPORT_COLUMNS, *reversed(_SETTINGS_COLUMNS)):
            batch.drop_column(column)
