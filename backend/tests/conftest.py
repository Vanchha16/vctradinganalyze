"""Test-session environment isolation.

`app/config/settings.py` builds a module-level `settings` singleton
(`get_settings()` is `@lru_cache`d) the first time `app.config.settings`
is imported anywhere - and its `model_config` reads `backend/.env`
(`SettingsConfigDict(env_file=".env", ...)`). Left alone, that means the
moment any test imports an app module, whatever real local configuration
happens to be in `.env` on this machine (e.g. `MARKET_DATA_PROVIDERS=
["twelve_data"]` plus a real `TWELVE_DATA_API_KEY`) gets loaded into the
test session, which:

1. Makes `test_get_market_data_providers_returns_rate_limited_mock`
   permanently fail on this machine (it asserts the documented `mock`
   default) while passing in CI, which has no `.env`.
2. Lets the suite make real, quota-consuming calls to the live Twelve
   Data API - observed exhausting the free tier's 800/day credit limit
   during a normal test run.

**Fix, and why it must live here specifically:** pydantic-settings'
precedence is init args > OS environment variables > `.env` file > field
defaults. `scripts/local_env.py` (the single canonical definition of
this override set - also used by `scripts/run_dev.py`'s launchers for a
manually-started `uvicorn`/Celery process, since this file only ever
protected the pytest session; see BACKLOG.md §11/§16 for the two
incidents that gap caused) sets these in `os.environ`, which overrides
`.env` without editing or reading that file (its secret values are
never touched). But this only works if that happens *before*
`Settings()` is first constructed - and pytest imports every
`conftest.py` before collecting test modules, so module scope here is
early enough, but ONLY because this file imports no `app.*` module
above the `apply_safe_overrides()` call below. If this module ever
gains an `app.*` import placed before it (e.g. a "tidy up the imports"
pass), `app.config.settings` would already be built from the ambient
environment by the time that call runs, and this whole file becomes a
silent no-op. Do not reorder. `scripts/local_env.py` carries the same
constraint and the full reasoning for each overridden value (including
why `ai_orchestrator_providers` itself is deliberately not among them) -
read it for the detail rather than duplicating it here.
"""

import sys
from pathlib import Path

# `backend/scripts/` has no `__init__.py` (not a package) - added to
# `sys.path` directly so `local_env` can be imported as a plain
# top-level module, the same way `scripts/run_dev.py` imports it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from local_env import apply_safe_overrides  # noqa: E402

apply_safe_overrides()

# Stdlib/third-party imports below carry no ordering constraint relative
# to the os.environ writes above - only `app.*` imports do (see module
# docstring). Kept after the writes anyway so the constraint is visually
# obvious to a future editor, not because it's technically required here.
import socket  # noqa: E402

import pytest  # noqa: E402

_real_connect = socket.socket.connect
_ALLOWED_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _guarded_connect(sock: socket.socket, address: tuple[str, int] | str) -> object:
    """Recommended-not-required safety net (build spec): the `.env`
    isolation above is what actually fixes the two known-failing tests;
    this only prevents the *class* of problem (a test silently reaching a
    real external service) from recurring. Loopback is allowed since
    local test infra (e.g. a real Redis on 127.0.0.1, mocked at a higher
    level in `test_quota.py`) isn't the "metered external vendor API"
    problem this guards against."""
    host = address[0] if isinstance(address, tuple) else address
    if host not in _ALLOWED_HOSTS:
        raise RuntimeError(
            f"Test attempted a real network connection to {address!r} - tests must "
            "never call an external service; use the project's Mock provider instead."
        )
    return _real_connect(sock, address)


@pytest.fixture(autouse=True)
def _block_external_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
