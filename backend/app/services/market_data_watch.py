"""Tells the operator on Telegram when prices stop arriving (ADR-188).

On 2026-11-05 production stopped writing candles at 03:03 UTC and nobody
knew for a day. This watch covers the failures the app itself can see - a
revoked or exhausted market-data key, a provider outage, a collector that
keeps failing. It cannot report its own server being down; an outside
uptime check covers that.

`decide` is pure. The per-asset "already alerted" marker lives in Redis,
like `ingestion_health` (ADR-139), so no migration is needed. Both Redis
calls fail open: an unreadable marker skips the asset for that run rather
than risking an alert on every run.
"""

import uuid
from datetime import datetime, timedelta
from enum import StrEnum

import redis
import structlog

from app.config import settings
from app.services.risk_management import session_classifier
from app.services.risk_management.types import MarketSession
from app.utils.time import as_aware_utc

logger = structlog.get_logger(__name__)

_redis_client: redis.Redis = redis.Redis.from_url(settings.redis_url)


class FreshnessAlert(StrEnum):
    STALE = "stale"
    RESUMED = "resumed"


def _market_open(moment: datetime) -> bool:
    return session_classifier.classify(as_aware_utc(moment)) is not MarketSession.CLOSED


def decide(newest: datetime | None, now: datetime, *, alerted: bool) -> FreshnessAlert | None:
    """One alert per episode:

    - **stale**: no new M1 candle for `market_data_stale_alert_minutes`, and
      the market was open for that whole time - so the weekend, and the first
      stretch after the Sunday reopen, never alert;
    - **resumed**: candles arriving again after a stale alert.

    The default 90 minutes clears gold's daily one-hour break."""
    threshold = timedelta(minutes=settings.market_data_stale_alert_minutes)
    stale = newest is None or as_aware_utc(now) - as_aware_utc(newest) >= threshold
    if stale and not alerted and _market_open(now) and _market_open(now - threshold):
        return FreshnessAlert.STALE
    if not stale and alerted:
        return FreshnessAlert.RESUMED
    return None


def _key(asset_id: uuid.UUID) -> str:
    return f"market_data_watch:alerted:{asset_id}"


def is_alerted(asset_id: uuid.UUID) -> bool | None:
    """`None` when Redis cannot be read - the caller skips the asset."""
    try:
        return bool(_redis_client.exists(_key(asset_id)))
    except Exception:  # noqa: BLE001 - fail open, same rule as ingestion_health
        logger.warning("market_data_watch.read_failed", asset_id=str(asset_id), exc_info=True)
        return None


def record(asset_id: uuid.UUID, alert: FreshnessAlert, now: datetime) -> None:
    try:
        if alert is FreshnessAlert.STALE:
            _redis_client.set(_key(asset_id), as_aware_utc(now).isoformat())
        else:
            _redis_client.delete(_key(asset_id))
    except Exception:  # noqa: BLE001 - fail open, same rule as ingestion_health
        logger.warning("market_data_watch.write_failed", asset_id=str(asset_id), exc_info=True)


__all__ = ["FreshnessAlert", "decide", "is_alerted", "record"]
