"""add failed login lockout columns to users

Revision ID: dea127b4db12
Revises: 6dd25f6c4947
Create Date: 2026-08-06 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "dea127b4db12"
down_revision: str | Sequence[str] | None = "6dd25f6c4947"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table (not plain op.add_column) - first ALTER of the
    # `users` table since f3a9c1d2e5b7, which hit SQLite's lack of
    # in-place ALTER support (BACKLOG.md §26). Not adding a constraint
    # here, but batch mode is used for every add-column-to-existing-table
    # migration in this project regardless, per that same institutional
    # knowledge entry.
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "failed_login_attempts", sa.Integer(), nullable=False, server_default="0"
            )
        )
        batch_op.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))

    # server_default only exists to backfill existing rows; drop it so the
    # ORM's Python-side default (0) is the single source of truth going
    # forward, matching f3a9c1d2e5b7's precedent for must_change_password.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("failed_login_attempts", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_attempts")
