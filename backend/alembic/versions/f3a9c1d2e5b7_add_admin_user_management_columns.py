"""add admin user management columns to users

Revision ID: f3a9c1d2e5b7
Revises: d4a1f9c2b7e3
Create Date: 2026-08-05 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3a9c1d2e5b7"
down_revision: str | Sequence[str] | None = "d4a1f9c2b7e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table (not plain op.add_column/create_foreign_key) - SQLite
    # has no `ALTER TABLE ... ADD CONSTRAINT`, only a copy-and-move strategy.
    # Postgres runs the same calls as a normal in-place ALTER; batch mode is
    # a no-op wrapper there, so this is safe/identical on both dialects.
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.add_column(sa.Column("created_by_admin_id", sa.Uuid(), nullable=True))
        batch_op.create_index("ix_users_deleted_at", ["deleted_at"], unique=False)
        batch_op.create_foreign_key(
            "fk_users_created_by_admin_id_users",
            "users",
            ["created_by_admin_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # server_default only exists to backfill existing rows; drop it so the
    # ORM's Python-side default (False) is the single source of truth going
    # forward, matching every other Boolean column on this model.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("must_change_password", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_created_by_admin_id_users", type_="foreignkey")
        batch_op.drop_index("ix_users_deleted_at")
        batch_op.drop_column("created_by_admin_id")
        batch_op.drop_column("must_change_password")
        batch_op.drop_column("deleted_at")
