"""fix smc_setup_state labels to the python enum member names

Revision ID: c5b81d4a2f07
Revises: a1c73f5e90d4
Create Date: 2026-09-23 10:00:00.000000

ADR-183 follow-up. `a1c73f5e90d4` created the type with the StrEnum's
*values* (`crt_anchor_confirmed`), but SQLAlchemy persists a Python enum by
its *member name* (`CRT_ANCHOR_CONFIRMED`) - which is also what every other
enum in this database uses (`signal_status` is DRAFT, ACTIVE, ...). So the
first real `smc.run` on production failed with:

    invalid input value for enum smc_setup_state: "CRT_ANCHOR_CONFIRMED"

The labels are renamed to the member names and the column default is moved
with them. `smc_setups` is empty, so no row needs converting; renaming
rather than recreating also keeps the table and its constraints untouched.

Schema-compatibility only: no state is added, removed or renamed in the
Python enum, and no strategy behaviour changes.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c5b81d4a2f07"
down_revision: str | Sequence[str] | None = "a1c73f5e90d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (value as created by a1c73f5e90d4, member name SQLAlchemy sends).
#: Mirrors `app.models.smc_setup.SmcSetupState`; the test asserts they match.
_RENAMES: tuple[tuple[str, str], ...] = (
    ("no_setup", "NO_SETUP"),
    ("crt_anchor_confirmed", "CRT_ANCHOR_CONFIRMED"),
    ("raid_confirmed", "RAID_CONFIRMED"),
    ("waiting_for_m5_mss", "WAITING_FOR_M5_MSS"),
    ("mss_confirmed", "MSS_CONFIRMED"),
    ("entry_zone_confirmed", "ENTRY_ZONE_CONFIRMED"),
    ("signal_created", "SIGNAL_CREATED"),
    ("expired", "EXPIRED"),
    ("cancelled", "CANCELLED"),
    ("traded", "TRADED"),
)
_DEFAULT = "CRT_ANCHOR_CONFIRMED"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite stores enums as text: there is no type to rename
    # The default references a label, so it has to be dropped before the
    # rename and re-set afterwards.
    op.execute("ALTER TABLE smc_setups ALTER COLUMN state DROP DEFAULT")
    for value, name in _RENAMES:
        op.execute(f"ALTER TYPE smc_setup_state RENAME VALUE '{value}' TO '{name}'")
    op.execute(f"ALTER TABLE smc_setups ALTER COLUMN state SET DEFAULT '{_DEFAULT}'")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE smc_setups ALTER COLUMN state DROP DEFAULT")
    for value, name in _RENAMES:
        op.execute(f"ALTER TYPE smc_setup_state RENAME VALUE '{name}' TO '{value}'")
    op.execute("ALTER TABLE smc_setups ALTER COLUMN state SET DEFAULT 'crt_anchor_confirmed'")
