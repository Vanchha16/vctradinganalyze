"""create api_credentials

Revision ID: 29015ec49225
Revises: a7c4e2b91d38
Create Date: 2026-09-10 10:28:22.137189

ADR-156: API keys editable from the admin UI, encrypted at rest.

**Hand-corrected after autogenerate.** `--autogenerate` also emitted
`drop_constraint` for `uq_telegram_accounts_link_code` and
`uq_telegram_accounts_user_id`. Those were removed: the constraints exist
in production Postgres and are declared on `TelegramAccount`. The
"difference" is an artifact of the local SQLite dev database, where an
earlier `batch_alter_table` rebuild lost the constraint *names*. Applying
them would have silently dropped real uniqueness guarantees - letting one
user link two Telegram accounts, or two users share a link code.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "29015ec49225"
down_revision: str | Sequence[str] | None = "a7c4e2b91d38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("hint", sa.String(length=8), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        # `sa.func.now()` rather than autogenerate's literal
        # `(CURRENT_TIMESTAMP)`, which is SQLite-flavoured - the rest of
        # this project's migrations use the portable form.
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # SET NULL, not CASCADE: deleting the admin who last rotated a key
        # must not delete the key itself and take an integration down.
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_api_credentials_name"), "api_credentials", ["name"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_api_credentials_name"), table_name="api_credentials")
    op.drop_table("api_credentials")
