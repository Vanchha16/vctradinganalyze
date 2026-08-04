"""create telegram_accounts table

Revision ID: d4a1f9c2b7e3
Revises: 72e726c08dd8
Create Date: 2026-08-03 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4a1f9c2b7e3"
down_revision: str | Sequence[str] | None = "72e726c08dd8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_accounts",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("link_code", sa.String(length=64), nullable=False),
        sa.Column("link_code_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_telegram_accounts_user_id"),
        sa.UniqueConstraint("link_code", name="uq_telegram_accounts_link_code"),
    )
    op.create_index(
        op.f("ix_telegram_accounts_user_id"), "telegram_accounts", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_telegram_accounts_link_code"), "telegram_accounts", ["link_code"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_telegram_accounts_link_code"), table_name="telegram_accounts")
    op.drop_index(op.f("ix_telegram_accounts_user_id"), table_name="telegram_accounts")
    op.drop_table("telegram_accounts")
