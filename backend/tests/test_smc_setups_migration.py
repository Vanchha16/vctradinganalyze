"""ADR-183 - the `smc_setups` migrations, checked against PostgreSQL's SQL.

The suite runs on SQLite, which has no enum *types* and stores enum columns
as text. It therefore cannot catch either of the two bugs that broke this
deployment on PostgreSQL on 2026-09-23:

1. the enum created twice in one transaction
   ("type smc_setup_state already exists"), and
2. the type's labels being the StrEnum's *values* while SQLAlchemy persists
   its *member names*
   ("invalid input value for enum smc_setup_state: CRT_ANCHOR_CONFIRMED").

These tests render the real PostgreSQL DDL through Alembic's offline mode -
no server needed - and assert both cannot come back.
"""

import re
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.models.smc_setup import SmcSetupState

CREATE_REVISION = "a1c73f5e90d4"
LABELS_REVISION = "c5b81d4a2f07"
HEAD_REVISION = "e7a4c19b3d52"
PREVIOUS = "b4e7d2a91c35"
BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_STATE = SmcSetupState.CRT_ANCHOR_CONFIRMED.name


def _render_sql(capsys: pytest.CaptureFixture[str], target: str) -> str:
    """The SQL PostgreSQL would run for `PREVIOUS:target`."""
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    # Offline mode: Alembic renders SQL for this dialect without connecting.
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://user:pw@localhost/db")
    command.upgrade(config, f"{PREVIOUS}:{target}", sql=True)
    return capsys.readouterr().out


def _final_labels(sql: str) -> list[str]:
    """The labels the type ends up with: those created, with every rename applied."""
    created = re.search(r"CREATE TYPE smc_setup_state AS ENUM \(([^)]*)\)", sql, re.IGNORECASE)
    assert created, "the type must be created"
    labels = [x.strip().strip("'") for x in created.group(1).split(",")]
    for old, new in re.findall(
        r"ALTER TYPE smc_setup_state RENAME VALUE '([^']+)' TO '([^']+)'", sql, re.IGNORECASE
    ):
        labels = [new if label == old else label for label in labels]
    labels += re.findall(
        r"ALTER TYPE smc_setup_state ADD VALUE IF NOT EXISTS '([^']+)'", sql, re.IGNORECASE
    )
    return labels


# --- 1 & 2: labels are the Python member names, never the values -----------
def test_every_enum_label_matches_a_python_member_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    labels = _final_labels(_render_sql(capsys, HEAD_REVISION))
    assert labels == [member.name for member in SmcSetupState], (
        "PostgreSQL labels must be exactly the Python enum member names, in order - "
        "that is what SQLAlchemy sends for a native enum"
    )


def test_no_lowercase_enum_value_survives_as_a_label(
    capsys: pytest.CaptureFixture[str],
) -> None:
    labels = set(_final_labels(_render_sql(capsys, HEAD_REVISION)))
    values = {member.value for member in SmcSetupState}
    assert not (labels & values), (
        f"these StrEnum values are still PostgreSQL labels: {sorted(labels & values)}. "
        "SQLAlchemy would send the member name and PostgreSQL would reject it."
    )
    assert all(label.isupper() for label in labels)


# --- 3: the column default is a valid label --------------------------------
def test_the_column_default_is_a_valid_member_name_label(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sql = _render_sql(capsys, HEAD_REVISION)
    labels = _final_labels(sql)
    defaults = re.findall(r"ALTER COLUMN state SET DEFAULT '([^']+)'", sql)
    assert defaults, "the column default must be re-set after the rename"
    assert defaults[-1] == DEFAULT_STATE
    assert defaults[-1] in labels


# --- 4 & 5: created once, table correct ------------------------------------
def test_the_enum_type_is_created_exactly_once(capsys: pytest.CaptureFixture[str]) -> None:
    sql = _render_sql(capsys, HEAD_REVISION)
    creates = re.findall(r"CREATE TYPE\s+smc_setup_state", sql, re.IGNORECASE)
    assert len(creates) == 1, (
        f"expected one CREATE TYPE for smc_setup_state, found {len(creates)}. "
        "Two is the first production failure this test exists to prevent."
    )


def test_the_table_is_created_and_references_the_type(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sql = _render_sql(capsys, CREATE_REVISION)
    assert re.search(r"CREATE TABLE\s+smc_setups", sql, re.IGNORECASE)
    assert re.search(r"state\s+smc_setup_state", sql, re.IGNORECASE)
    assert "uq_smc_setups_asset_anchor" in sql


# --- 6: nothing existing is touched ----------------------------------------
def test_no_existing_table_is_altered_or_dropped(capsys: pytest.CaptureFixture[str]) -> None:
    """BBMA's data must be untouched by this deployment."""
    sql = _render_sql(capsys, HEAD_REVISION)
    assert not re.search(
        r"ALTER TABLE\s+(signals|ai_analysis|price_candles|assets|ea_tokens|users)",
        sql, re.IGNORECASE,
    )
    assert not re.search(r"DROP TABLE", sql, re.IGNORECASE)
    # The only ALTER TABLE touches the new table's own column default.
    assert all(
        target == "smc_setups"
        for target in re.findall(r"ALTER TABLE\s+(\w+)", sql, re.IGNORECASE)
    )


def test_the_revision_chain_is_what_production_expects(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sql = _render_sql(capsys, HEAD_REVISION)
    assert f"WHERE alembic_version.version_num = '{PREVIOUS}'" in sql
    assert f"UPDATE alembic_version SET version_num='{CREATE_REVISION}'" in sql
    assert f"UPDATE alembic_version SET version_num='{LABELS_REVISION}'" in sql
    assert f"UPDATE alembic_version SET version_num='{HEAD_REVISION}'" in sql


def test_the_downgrade_restores_the_previous_labels(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://user:pw@localhost/db")
    command.downgrade(config, f"{LABELS_REVISION}:{CREATE_REVISION}", sql=True)
    sql = capsys.readouterr().out
    renames = re.findall(
        r"ALTER TYPE smc_setup_state RENAME VALUE '([^']+)' TO '([^']+)'", sql, re.IGNORECASE
    )
    original = [m.value for m in SmcSetupState if m is not SmcSetupState.EXECUTION_REJECTED]
    assert [new for _, new in renames] == original


def test_the_execution_rejected_label_is_added_once_outside_a_transaction(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """PostgreSQL cannot use a new enum value in the transaction that added
    it, so the ADD VALUE must run in its own autocommit block."""
    sql = _render_sql(capsys, HEAD_REVISION)
    adds = re.findall(
        r"ALTER TYPE smc_setup_state ADD VALUE IF NOT EXISTS 'EXECUTION_REJECTED'", sql
    )
    assert len(adds) == 1
    before = sql[: sql.index(adds[0])]
    assert before.rstrip().endswith("COMMIT;"), "ADD VALUE must follow a COMMIT (autocommit block)"
