"""fix telegram_accounts unique indexes (drop separate unique constraints)

Revision ID: 33eb66dc1919
Revises: dea127b4db12
Create Date: 2026-08-12 05:05:00.000000

Reconciles migration `d4a1f9c2b7e3` (which created a separate
`UniqueConstraint` plus a non-unique index per column) with the
`TelegramAccount` model's actual current shape (`unique=True, index=True`
on `mapped_column`, which SQLAlchemy renders as a single unique index) -
this drift was never caught until CI's `alembic check` gate was fixed to
actually run (Phase 9H CI repair).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "33eb66dc1919"
down_revision: str | Sequence[str] | None = "dea127b4db12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_telegram_accounts_link_code", "telegram_accounts", type_="unique")
    op.drop_constraint("uq_telegram_accounts_user_id", "telegram_accounts", type_="unique")
    op.drop_index(op.f("ix_telegram_accounts_link_code"), table_name="telegram_accounts")
    op.drop_index(op.f("ix_telegram_accounts_user_id"), table_name="telegram_accounts")
    op.create_index(
        op.f("ix_telegram_accounts_link_code"), "telegram_accounts", ["link_code"], unique=True
    )
    op.create_index(
        op.f("ix_telegram_accounts_user_id"), "telegram_accounts", ["user_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_telegram_accounts_user_id"), table_name="telegram_accounts")
    op.drop_index(op.f("ix_telegram_accounts_link_code"), table_name="telegram_accounts")
    op.create_index(
        op.f("ix_telegram_accounts_user_id"), "telegram_accounts", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_telegram_accounts_link_code"), "telegram_accounts", ["link_code"], unique=False
    )
    op.create_unique_constraint(
        "uq_telegram_accounts_user_id", "telegram_accounts", ["user_id"]
    )
    op.create_unique_constraint(
        "uq_telegram_accounts_link_code", "telegram_accounts", ["link_code"]
    )
