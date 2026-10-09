"""ADR-185 - the `smc_v2_setups` migration, rendered as PostgreSQL SQL.

No PostgreSQL server is needed: Alembic's offline mode renders the DDL the
production database would run (the pattern of test_smc_setups_migration.py).
The migration must be additive - one new table, nothing existing altered.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command

REVISION = "e4c9a2f7b1d6"
PREVIOUS = "d7c4a9e1f203"  # production's head before v2
BACKEND = Path(__file__).resolve().parents[1]


def _config() -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://user:pw@localhost/db")
    return config


def _render(capsys: pytest.CaptureFixture[str]) -> str:
    command.upgrade(_config(), f"{PREVIOUS}:{REVISION}", sql=True)
    return capsys.readouterr().out


def test_the_migration_is_the_single_head_on_top_of_production():
    script = ScriptDirectory.from_config(_config())
    assert script.get_heads() == [REVISION]
    assert script.get_revision(REVISION).down_revision == PREVIOUS


def test_it_creates_only_the_new_table_and_its_indexes(capsys: pytest.CaptureFixture[str]):
    sql = _render(capsys).upper()
    assert "CREATE TABLE SMC_V2_SETUPS" in sql
    for forbidden in ("DROP TABLE", "ALTER TABLE SMC_SETUPS", "ALTER TABLE SIGNALS",
                      "ALTER TABLE PRICE_CANDLES", "CREATE TYPE"):
        assert forbidden not in sql, forbidden
    assert sql.count("CREATE TABLE") == 1


def test_the_durable_identity_and_signal_link_are_unique(capsys: pytest.CaptureFixture[str]):
    sql = _render(capsys)
    assert "uq_smc_v2_setups_identity" in sql
    assert "UNIQUE (asset_id, strategy, design, anchor_timeframe, anchor_t)" in sql
    assert "uq_smc_v2_setups_signal_id" in sql


def test_downgrade_drops_only_the_new_table(capsys: pytest.CaptureFixture[str]):
    command.downgrade(_config(), f"{REVISION}:{PREVIOUS}", sql=True)
    sql = capsys.readouterr().out.upper()
    assert "DROP TABLE SMC_V2_SETUPS" in sql and sql.count("DROP TABLE") == 1
