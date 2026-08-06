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
defaults. Setting these in `os.environ` overrides `.env` without editing
or reading that file (its secret values are never touched). But this
only works if these `os.environ` writes happen *before* `Settings()` is
first constructed - and pytest imports every `conftest.py` before
collecting test modules, so module scope here is early enough, but ONLY
because this file imports no `app.*` module above the writes below. If
this module ever gains an `app.*` import placed before them (e.g. a
"tidy up the imports" pass), `app.config.settings` would already be
built from the ambient environment by the time these lines run, and this
whole file becomes a silent no-op. Do not reorder.

Values below are each field's own documented default in
`app/config/settings.py` - not invented here - so this simply guarantees
the test session runs with the same provider configuration CI already
has, regardless of what a developer's local `.env` happens to contain.
`ai_orchestrator_providers` is deliberately not overridden: unlike the
other provider lists, it has no `"mock"` implementation
(`app/dependencies/ai_orchestrator.py`'s `_PROVIDER_FACTORIES` maps only
`"openai"`) - `"openai"` *is* its correct default. Blanking
`OPENAI_API_KEY` is what actually neutralises it: `OpenAIProvider.
generate()` raises `AIProviderConfigurationError` immediately when the
key is empty (`openai_provider.py:72-74`), so an accidental real call
fails loudly instead of silently reaching the live API - the same
belt-and-braces treatment as `TWELVE_DATA_API_KEY`/`NEWS_API_KEY`/
`ECONOMIC_API_KEY`/`TELEGRAM_BOT_TOKEN` below. Pydantic-settings expects
list-typed fields to arrive from the environment as JSON, matching how
`.env` itself already encodes them (e.g. `MARKET_DATA_PROVIDERS=
["twelve_data"]`).
"""

import os

os.environ["MARKET_DATA_PROVIDERS"] = '["mock"]'
os.environ["TWELVE_DATA_API_KEY"] = ""
os.environ["NEWS_PROVIDERS"] = '["mock"]'
os.environ["NEWS_API_KEY"] = ""
os.environ["ECONOMIC_CALENDAR_PROVIDERS"] = '["mock"]'
os.environ["ECONOMIC_API_KEY"] = ""
os.environ["TELEGRAM_PROVIDERS"] = '["mock"]'
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["OPENAI_API_KEY"] = ""

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
