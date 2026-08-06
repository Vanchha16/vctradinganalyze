"""Phase 9C (docs/60 §7) - `scripts/seed_e2e_data.py`'s safety refusal
must never let a `DATABASE_URL` pointing anywhere but the local `e2e.db`
file through. Tests `e2e_db.assert_safe_e2e_target` directly rather than
running the seed script itself, since the function has no `app.*`
dependency and importing the script would trigger real database I/O.
"""

import pytest
from e2e_db import E2E_DATABASE_URL, assert_safe_e2e_target


def test_accepts_the_canonical_e2e_database_url() -> None:
    assert_safe_e2e_target(E2E_DATABASE_URL)  # must not raise


def test_rejects_postgres() -> None:
    with pytest.raises(SystemExit):
        assert_safe_e2e_target("postgresql+psycopg://trading_user:x@localhost:5432/trading_app")


def test_rejects_a_production_looking_postgres_url() -> None:
    with pytest.raises(SystemExit):
        assert_safe_e2e_target("postgresql+psycopg://user:pass@prod-db.example.com:5432/trading_app")


def test_rejects_dev_db() -> None:
    """The single most important case: a misconfigured `DATABASE_URL`
    must never let this script wipe/reseed the real local dev database."""
    with pytest.raises(SystemExit):
        assert_safe_e2e_target("sqlite:///./dev.db")


def test_rejects_sqlite_in_memory() -> None:
    with pytest.raises(SystemExit):
        assert_safe_e2e_target("sqlite:///:memory:")


def test_rejects_an_arbitrary_sqlite_file() -> None:
    with pytest.raises(SystemExit):
        assert_safe_e2e_target("sqlite:////tmp/whatever.db")


def test_accepts_an_absolute_path_to_e2e_db() -> None:
    """Only the filename is checked, not the exact path form - a caller
    running from a different `cwd` still resolves to the same file."""
    assert_safe_e2e_target("sqlite:////absolute/path/to/e2e.db")  # must not raise
