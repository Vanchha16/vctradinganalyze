"""Tiny per-chat conversation state for the Telegram bot's "Show Chart"
button (§13): tapping it prompts the user to type a symbol as a plain
follow-up message, so `telegram_tasks.py`'s poll loop needs to remember,
for a short window, that the *next* free-text message from that chat is
a symbol reply rather than an ordinary ignored message.

Backed by Redis with a short TTL rather than a DB column - this is
throwaway UI state, not a durable fact about the account (same
reasoning as this project's existing Redis-backed rate limiting/quota
counters, `app/utils/redis_fixed_window.py`), and it must self-expire so
a user who taps the button and never replies doesn't have every future
message misinterpreted as a symbol.
"""

from app.core.redis_pubsub import get_sync_redis

_KEY_PREFIX = "telegram:awaiting_chart_symbol:"
_TTL_SECONDS = 300


def _key(chat_id: str) -> str:
    return f"{_KEY_PREFIX}{chat_id}"


def mark_awaiting_chart_symbol(chat_id: str) -> None:
    """Fail-open: if Redis is unreachable, the worst case is the user's
    next message isn't recognized as a symbol reply and they have to tap
    the button again - never worth failing the callback handler over."""
    try:
        get_sync_redis().setex(_key(chat_id), _TTL_SECONDS, "1")
    except Exception:
        pass


def consume_awaiting_chart_symbol(chat_id: str) -> bool:
    """Returns whether `chat_id` was awaiting a symbol, and clears the
    flag either way - one text message answers the prompt, whether or
    not it turns out to be a valid symbol (an invalid one asks the user
    to tap the button again, rather than leaving the flag armed for an
    unrelated later message to accidentally consume)."""
    try:
        key = _key(chat_id)
        was_set = get_sync_redis().getdel(key)
        return bool(was_set)
    except Exception:
        return False


__all__ = ["consume_awaiting_chart_symbol", "mark_awaiting_chart_symbol"]
