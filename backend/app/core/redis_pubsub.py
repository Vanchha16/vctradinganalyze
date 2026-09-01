import json
from collections.abc import AsyncGenerator
from typing import Any, cast

import redis
import redis.asyncio as aioredis
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# Synchronous Redis client for Celery tasks / sync services
_sync_redis: redis.Redis | None = None
# Async Redis client for FastAPI async endpoints & WebSocket tasks
_async_redis: aioredis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = redis.Redis.from_url(settings.redis_url)
    return _sync_redis


def get_async_redis() -> aioredis.Redis:
    global _async_redis
    if _async_redis is None:
        _async_redis = cast(aioredis.Redis, aioredis.from_url(settings.redis_url))  # type: ignore[no-untyped-call]
    return _async_redis


def publish_event_sync(channel: str, data: dict[str, Any] | list[Any] | str) -> bool:
    """Publish an event to a Redis channel synchronously (for worker/sync contexts).

    Fails open: logs a warning if Redis is unreachable and returns False.
    """
    try:
        payload = json.dumps(data) if not isinstance(data, str) else data
        client = get_sync_redis()
        client.publish(channel, payload)
        return True
    except Exception as exc:
        logger.warning("redis_pubsub.sync_publish_failed", channel=channel, error=str(exc))
        return False


async def publish_event_async(channel: str, data: dict[str, Any] | list[Any] | str) -> bool:
    """Publish an event to a Redis channel asynchronously (for FastAPI async contexts).

    Fails open: logs a warning if Redis is unreachable and returns False.
    """
    try:
        payload = json.dumps(data) if not isinstance(data, str) else data
        client = get_async_redis()
        await client.publish(channel, payload)
        return True
    except Exception as exc:
        logger.warning("redis_pubsub.async_publish_failed", channel=channel, error=str(exc))
        return False


async def subscribe_channel(channel: str) -> AsyncGenerator[dict[str, Any] | str, None]:
    """Async generator that subscribes to a Redis channel and yields received messages."""
    client = get_async_redis()
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message is not None and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    parsed = json.loads(data)
                    yield parsed
                except Exception:
                    yield data
    finally:
        await pubsub.unsubscribe(channel)
        if hasattr(pubsub, "aclose"):
            await pubsub.aclose()  # type: ignore[no-untyped-call]


def get_price_channel(symbol: str, timeframe: str) -> str:
    return f"prices:{symbol.strip().upper()}:{timeframe.strip().lower()}"


def get_signal_channel() -> str:
    return "signals:updates"
