"""add EXECUTION_REJECTED to smc_setup_state

Revision ID: e7a4c19b3d52
Revises: c5b81d4a2f07
Create Date: 2026-09-25 05:00:00.000000

ADR-183 follow-up (audit D2/D3). A signal refused at execution - impossible
stop/entry geometry, or a live broker/EA rejection - gets its own terminal
state instead of being recorded as a trade. The label is the Python member
name, as SQLAlchemy persists it (see c5b81d4a2f07).

PostgreSQL cannot use a newly added enum value inside the transaction that
added it, so the ADD VALUE runs in its own autocommit block. Nothing else
changes: no column, no constraint, no existing row.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7a4c19b3d52"
down_revision: str | Sequence[str] | None = "c5b81d4a2f07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return  # SQLite stores enum columns as text: no type to extend
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE smc_setup_state ADD VALUE IF NOT EXISTS 'EXECUTION_REJECTED'")


def downgrade() -> None:
    # PostgreSQL cannot drop a value from an enum type. The extra label is
    # inert for the previous code, which never writes it, so a downgrade
    # leaves it in place rather than rebuilding the type under live rows.
    pass
