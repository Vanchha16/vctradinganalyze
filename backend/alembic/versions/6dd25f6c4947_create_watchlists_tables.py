"""create watchlists tables

Revision ID: 6dd25f6c4947
Revises: f3a9c1d2e5b7
Create Date: 2026-08-06 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6dd25f6c4947"
down_revision: str | Sequence[str] | None = "f3a9c1d2e5b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlists",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_watchlists_user_id"), "watchlists", ["user_id"], unique=False)

    op.create_table(
        "watchlist_items",
        sa.Column("watchlist_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["watchlist_id"], ["watchlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "watchlist_id", "asset_id", name="uq_watchlist_items_watchlist_asset"
        ),
    )
    op.create_index(
        op.f("ix_watchlist_items_watchlist_id"), "watchlist_items", ["watchlist_id"], unique=False
    )
    op.create_index(
        op.f("ix_watchlist_items_asset_id"), "watchlist_items", ["asset_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_watchlist_items_asset_id"), table_name="watchlist_items")
    op.drop_index(op.f("ix_watchlist_items_watchlist_id"), table_name="watchlist_items")
    op.drop_table("watchlist_items")
    op.drop_index(op.f("ix_watchlists_user_id"), table_name="watchlists")
    op.drop_table("watchlists")
