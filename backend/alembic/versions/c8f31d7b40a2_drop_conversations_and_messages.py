"""drop conversations and messages tables (AI Chat removal)

Revision ID: c8f31d7b40a2
Revises: b2c7e4a91f3d
Create Date: 2026-09-08 00:00:00.000000

ADR-143: the AI Chat Assistant (Phase 6C, docs/52) is removed entirely -
frontend, backend and persistence. This migration is the irreversible
part: it destroys every stored conversation and message.

The production data was exported before this ran
(`~/deploy_backups/ai_chat_tables_*.dump` / `.sql`, 4 conversations /
18 messages, last used 2026-08-12). `downgrade()` recreates the empty
schema - it cannot bring the rows back.

The two Postgres enum types are dropped explicitly. `sa.Enum` inside
`create_table` auto-creates the type, but `drop_table` does *not*
remove it - migration 72e726c08dd8's own downgrade left both behind.
SQLite has no enum types, hence the dialect check.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8f31d7b40a2"
down_revision: str | Sequence[str] | None = "b2c7e4a91f3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `messages` first - it holds the FK to `conversations`.
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_table("conversations")

    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="message_role").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="conversation_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Recreates the schema only - the rows are gone. Mirrors
    72e726c08dd8's `upgrade()`."""
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("current_symbol", sa.String(length=20), nullable=True),
        sa.Column(
            "current_timeframe",
            sa.Enum(
                "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN", name="candle_timeframe"
            ),
            nullable=True,
        ),
        sa.Column(
            "status", sa.Enum("ACTIVE", "ARCHIVED", name="conversation_status"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False)
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Enum("USER", "ASSISTANT", name="message_role"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column(
            "timeframe",
            sa.Enum(
                "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN", name="candle_timeframe"
            ),
            nullable=True,
        ),
        sa.Column("ai_analysis_id", sa.Uuid(), nullable=True),
        sa.Column("signal_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["ai_analysis_id"], ["ai_analysis.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False
    )
