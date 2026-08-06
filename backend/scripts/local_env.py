"""Canonical "safe local config" - the one place that defines which
`os.environ` overrides force every real vendor provider back to its
`app/config/settings.py` `"mock"` default and blank every real API key.

Used by two callers: `backend/tests/conftest.py` (the pytest session)
and `backend/scripts/run_dev.py` (manually-started `uvicorn`/Celery
worker/beat). Before this module existed, `conftest.py` hardcoded this
list itself, and nothing at all protected a manually-started process -
which is how a real Twelve Data quota got exhausted and a real NewsAPI
call went out during local development (BACKLOG.md §11/§16). Sharing one
definition means a future provider addition can't drift the two apart
silently.

**Critical constraint - read this before changing anything here or in a
caller:** `app/config/__init__.py` builds a module-level `settings`
singleton (`get_settings()` is `@lru_cache`d) the first time
`app.config.settings` is imported anywhere, and its `model_config` reads
`backend/.env`. pydantic-settings' precedence is init args > OS
environment variables > `.env` file > field defaults, so writing to
`os.environ` overrides `.env` - but only if that write happens *before*
`Settings()` is first constructed. This module must therefore import
**no `app.*` module** (so importing it can never accidentally trigger
that construction), and every caller must call `apply_safe_overrides()`
**before** its own first `app.*` import. If a caller ever imports
`app.config.settings` (directly or transitively) before calling this,
the override becomes a silent no-op - the ambient `.env` wins instead.

Values below are each field's own documented default in
`app/config/settings.py` - not invented here. `ai_orchestrator_providers`
is deliberately not included: it has no `"mock"` implementation
(`app/dependencies/ai_orchestrator.py`'s `_PROVIDER_FACTORIES` maps only
`"openai"`) - `"openai"` *is* its correct default, and blanking
`OPENAI_API_KEY` is what neutralises it instead (`OpenAIProvider.
generate()` raises immediately on an empty key). Pydantic-settings
expects list-typed fields to arrive from the environment as JSON,
matching how `.env` itself already encodes them.
"""

import os
from collections.abc import MutableMapping

SAFE_LOCAL_OVERRIDES: dict[str, str] = {
    "MARKET_DATA_PROVIDERS": '["mock"]',
    "TWELVE_DATA_API_KEY": "",
    "NEWS_PROVIDERS": '["mock"]',
    "NEWS_API_KEY": "",
    "ECONOMIC_CALENDAR_PROVIDERS": '["mock"]',
    "ECONOMIC_API_KEY": "",
    "TELEGRAM_PROVIDERS": '["mock"]',
    "TELEGRAM_BOT_TOKEN": "",
    "OPENAI_API_KEY": "",
}

#: Which override keys are secrets (API keys/tokens) - never print their
#: *value* to a console/log, even the safe blank-string override value,
#: so a banner-printing caller can't accidentally grow a habit of
#: printing this dict's values wholesale once a real key is in play.
SECRET_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {
        "TWELVE_DATA_API_KEY",
        "NEWS_API_KEY",
        "ECONOMIC_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "OPENAI_API_KEY",
    }
)


def apply_safe_overrides(
    env: MutableMapping[str, str] | None = None,
) -> MutableMapping[str, str]:
    """Writes `SAFE_LOCAL_OVERRIDES` into `env` (defaults to `os.environ`)
    and returns it. Call this before any `app.*` import - see the module
    docstring."""
    target: MutableMapping[str, str] = os.environ if env is None else env
    target.update(SAFE_LOCAL_OVERRIDES)
    return target
