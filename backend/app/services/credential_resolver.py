"""Where an API key actually comes from at call time (ADR-156).

Database first, environment second. That order is what lets a key edited
in the admin UI take effect without a redeploy, while keeping every
existing deployment working untouched: with no row present, every caller
gets exactly the `.env` value it got before this existed.

**Why this can work without restarting anything.** Every consumer reads
its key at call or construction time, not into a module-level constant at
import: `dependencies/market_data.py`, `dependencies/news.py` and
`dependencies/telegram.py` build their providers per request and per
Celery task, and `openai_provider` reads on each request. So swapping the
source here propagates on the next call. ADR-154 assumed this would need
a worker restart; checking the call sites showed it does not.

A short in-process cache keeps this from adding a database round trip to
every provider construction, at the cost of a stored key taking up to
`_CACHE_TTL_SECONDS` to take effect - stated in the admin UI rather than
left as a surprise.
"""

import time
from typing import Literal

import structlog

from app.config import settings
from app.core import credential_crypto
from app.database.session import SessionLocal
from app.repositories.api_credential_repository import ApiCredentialRepository

logger = structlog.get_logger(__name__)

CredentialName = Literal["twelve_data", "news_api", "openai", "telegram_bot"]

#: The complete set of keys this feature manages, and the `Settings`
#: attribute each falls back to. Adding a key means adding it here and
#: nowhere else.
FALLBACK_SETTING: dict[CredentialName, str] = {
    "twelve_data": "twelve_data_api_key",
    "news_api": "news_api_key",
    "openai": "openai_api_key",
    "telegram_bot": "telegram_bot_token",
}

#: Long enough that provider construction is not a query per call, short
#: enough that "I pasted a new key" feels immediate.
_CACHE_TTL_SECONDS = 30.0

#: Caches the DATABASE LOOKUP - the stored value, or `None` for "no row" -
#: never the resolved answer. Caching the answer would pin the `.env`
#: fallback too, so a change to the environment could be served stale for
#: up to the TTL. It also leaked between tests that monkeypatch a settings
#: key, which is how the distinction was found.
_cache: dict[str, tuple[str | None, float]] = {}


def resolve(name: CredentialName) -> str:
    """The key to use right now: stored value if present, else `.env`.

    Never raises for a missing row - an absent credential is simply the
    environment's value, which may itself be empty. Callers already treat
    an empty key as "provider not configured" and that behaviour is
    unchanged.
    """
    # Read live on every call: it is a dict lookup, and caching it is what
    # made a monkeypatched or edited environment value go stale.
    env_value = str(getattr(settings, FALLBACK_SETTING[name], "") or "")

    if not credential_crypto.is_configured():
        return env_value

    cached = _cache.get(name)
    if cached is not None and cached[1] > time.monotonic():
        stored = cached[0]
    else:
        stored = _read_stored(name)
        _cache[name] = (stored, time.monotonic() + _CACHE_TTL_SECONDS)

    return stored if stored is not None else env_value


def invalidate(name: CredentialName | None = None) -> None:
    """Called on write so the operator's own next request reflects the
    change immediately, rather than waiting out the TTL in the process
    that just handled the update."""
    if name is None:
        _cache.clear()
    else:
        _cache.pop(name, None)


def _read_stored(name: CredentialName) -> str | None:
    """Opens its own short-lived session: this is called from provider
    construction, which has no request session to borrow, and from Celery
    tasks that build their own graph.

    Fails open to the environment value. A database hiccup should degrade
    to the previous behaviour, not take market data down.
    """
    session = SessionLocal()
    try:
        row = ApiCredentialRepository(session).get_by_name(name)
        if row is None:
            return None
        return credential_crypto.decrypt(row.encrypted_value)
    except Exception:  # noqa: BLE001 - fail open, same rule ingestion_health follows
        logger.warning("credential_resolver.read_failed", credential=name, exc_info=True)
        return None
    finally:
        session.close()


__all__ = ["FALLBACK_SETTING", "CredentialName", "invalidate", "resolve"]
