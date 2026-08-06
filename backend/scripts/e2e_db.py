"""Single source of truth for the E2E test database target (Phase 9C,
docs/60 §7). Imported by both `run_dev.py --e2e-db` (points a manually
started backend at it) and `seed_e2e_data.py` (seeds it) - two callers
sharing one definition, the same pattern `local_env.py` already
established for the mock-provider overrides.

No `app.*` import here (same constraint `local_env.py` documents) - this
module must be safe to import before `DATABASE_URL` is set.
"""

from pathlib import Path

#: Always relative to `backend/` (both callers run with that as `cwd`),
#: never `dev.db` - a dedicated file so E2E runs never depend on, or
#: corrupt, whatever manual-verification state happens to be in `dev.db`.
E2E_DB_FILENAME = "e2e.db"
E2E_DATABASE_URL = f"sqlite:///./{E2E_DB_FILENAME}"


def assert_safe_e2e_target(database_url: str) -> None:
    """Refuse to proceed unless `database_url` is unambiguously the local
    E2E SQLite file.

    A seed script that creates a known-password admin account is a
    serious hazard if it can ever point at a real database - this is the
    explicit safety requirement from the build spec (§2), not a
    hypothetical. Rejects anything that isn't `sqlite:///` (Postgres,
    including production, is instantly rejected by dialect alone) and
    additionally requires the filename to be exactly `e2e.db`, so a
    misconfigured `DATABASE_URL` pointing at `dev.db` (or anything else)
    is refused too, not just non-SQLite targets.
    """
    if not database_url.startswith("sqlite:///"):
        raise SystemExit(
            f"Refusing to seed: DATABASE_URL {database_url!r} is not a local SQLite "
            "database. seed_e2e_data.py must never run against Postgres or any "
            "non-local target."
        )

    filename = Path(database_url.removeprefix("sqlite:///")).name
    if filename != E2E_DB_FILENAME:
        raise SystemExit(
            f"Refusing to seed: target file is {filename!r}, expected "
            f"{E2E_DB_FILENAME!r}. This guards against accidentally wiping dev.db "
            "or any other database."
        )
