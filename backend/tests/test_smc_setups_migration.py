"""ADR-183 - the `smc_setups` migration, checked against PostgreSQL's SQL.

The suite runs on SQLite, which has no enum *types*, so it cannot catch the
one thing that actually broke this migration in production on 2026-09-23:
the enum being created twice in the same transaction
("type smc_setup_state already exists").

These tests render the migration's real PostgreSQL DDL through Alembic's
offline mode - no server needed - and assert the type is created exactly
once, and that `create_table` only references it.
"""

import re
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command

REVISION = "a1c73f5e90d4"
PREVIOUS = "b4e7d2a91c35"
BACKEND = Path(__file__).resolve().parents[1]


def _render_sql(capsys: pytest.CaptureFixture[str]) -> str:
    """The SQL PostgreSQL would run for this one revision."""
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    # Offline mode: Alembic renders SQL for this dialect without connecting.
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://user:pw@localhost/db")
    command.upgrade(config, f"{PREVIOUS}:{REVISION}", sql=True)
    return capsys.readouterr().out


def test_the_enum_type_is_created_exactly_once(capsys: pytest.CaptureFixture[str]) -> None:
    sql = _render_sql(capsys)
    creates = re.findall(r"CREATE TYPE\s+smc_setup_state", sql, re.IGNORECASE)
    assert len(creates) == 1, (
        f"expected one CREATE TYPE for smc_setup_state, found {len(creates)}. "
        "Two is the production failure this test exists to prevent."
    )


def test_the_table_is_created_and_references_the_type(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sql = _render_sql(capsys)
    assert re.search(r"CREATE TABLE\s+smc_setups", sql, re.IGNORECASE)
    assert re.search(r"state\s+smc_setup_state\s+DEFAULT\s+'crt_anchor_confirmed'", sql, re.I)
    assert "uq_smc_setups_asset_anchor" in sql


def test_no_existing_table_is_altered(capsys: pytest.CaptureFixture[str]) -> None:
    """BBMA's data must be untouched by this deployment."""
    sql = _render_sql(capsys)
    assert not re.search(r"ALTER TABLE\s+(signals|ai_analysis|price_candles|assets|ea_tokens)",
                         sql, re.IGNORECASE)
    assert not re.search(r"DROP TABLE", sql, re.IGNORECASE)


def test_the_revision_chain_is_what_production_expects(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sql = _render_sql(capsys)
    assert f"UPDATE alembic_version SET version_num='{REVISION}'" in sql
    assert f"WHERE alembic_version.version_num = '{PREVIOUS}'" in sql
