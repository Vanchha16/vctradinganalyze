"""Audit D9 - migration b2d6f0a8c914, checked against PostgreSQL's SQL.

Rendered through Alembic's offline mode (no server needed), like the
smc_setups migration tests: the suite's SQLite cannot show what PostgreSQL
would run.
"""

import re
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.models.price_candle import PriceCandle

PREVIOUS = "e7a4c19b3d52"
REVISION = "b2d6f0a8c914"
BACKEND = Path(__file__).resolve().parents[1]


def _config() -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://user:pw@localhost/db")
    return config


def test_upgrade_adds_one_nullable_timestamptz_column_and_nothing_else(
    capsys: pytest.CaptureFixture[str],
) -> None:
    command.upgrade(_config(), f"{PREVIOUS}:{REVISION}", sql=True)
    sql = capsys.readouterr().out

    added = re.findall(r"ALTER TABLE price_candles ADD COLUMN fetched_at ([^;]+);", sql)
    assert added == ["TIMESTAMP WITH TIME ZONE"], added  # nullable, no default
    # No backfill and no other table or row touched.
    assert not re.search(r"\bUPDATE price_candles\b", sql)
    statements = [s for s in re.findall(r"^(?:ALTER|CREATE|DROP|UPDATE|INSERT)\b.*", sql, re.M)
                  if "alembic_version" not in s]
    assert statements == [
        "ALTER TABLE price_candles ADD COLUMN fetched_at TIMESTAMP WITH TIME ZONE;"
    ]
    assert f"UPDATE alembic_version SET version_num='{REVISION}'" in sql


def test_downgrade_drops_only_that_column(capsys: pytest.CaptureFixture[str]) -> None:
    command.downgrade(_config(), f"{REVISION}:{PREVIOUS}", sql=True)
    sql = capsys.readouterr().out
    assert "ALTER TABLE price_candles DROP COLUMN fetched_at;" in sql
    assert not re.search(r"DROP TABLE", sql)


def test_model_and_migration_agree() -> None:
    column = PriceCandle.__table__.c.fetched_at
    assert column.nullable is True
    assert column.type.timezone is True
    assert column.server_default is None
