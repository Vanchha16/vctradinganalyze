from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import structlog
from celery.schedules import crontab

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.market_data import get_market_data_providers
from app.dependencies.telegram import get_telegram_provider
from app.models.enums import Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.telegram_account_repository import TelegramAccountRepository
from app.services import credential_resolver, market_data_watch
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.timeframe_utils import TIMEFRAME_DURATIONS
from app.services.market_data_service import MarketDataService
from app.services.market_data_watch import FreshnessAlert
from app.services.paper_swing_service import REQUESTS_PER_DAY as _PAPER_SWING_REQUESTS
from app.services.telegram.message_sections import (
    compose_market_data_resumed_message,
    compose_market_data_stale_message,
)
from app.services.telegram_service import TelegramService
from app.utils.time import as_aware_utc
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

# A small lookback multiplier so a run that's late (or a missed tick) still
# catches up on the intervening candles - the collection itself is
# idempotent (PriceCandleRepository.upsert), so re-fetching overlap is safe.
_LOOKBACK_INTERVALS = 5
# ADR-171 - and never less than this many of the timeframe's own run
# intervals, so a candle the provider has not published yet at one run is
# still inside the window of the next ones.
_LOOKBACK_RUNS = 3


def build_beat_schedule_seconds(
    min_interval_seconds: float,
    overrides: dict[str, float] | None = None,
) -> dict[Timeframe, float]:
    """Celery Beat interval (seconds) per timeframe - shorter timeframes are
    polled more often, matching how often a new candle actually forms, but
    never more often than `min_interval_seconds` (Phase 9H, ADR-140) -
    timeframes already longer than the floor are unaffected by `max()`
    here. A plain function, not just a module-level dict comprehension, so
    the floor's effect on the schedule is directly testable without
    reimporting the module for a different setting value.

    ADR-141: `overrides` (keyed by `Timeframe` value, e.g. `"M1"`) wins
    over both the timeframe's own duration and the floor - it is the
    operator's deliberate opt-out, including going *faster* than the
    floor, which is the only lever on signal SL/TP detection latency.
    An unrecognised key is ignored rather than raising: this is
    operator-supplied config read at import time, and a typo must not
    prevent the worker from starting. `log_quota_projection` remains the
    guard that makes an over-budget schedule visible."""
    schedule = {
        timeframe: max(duration.total_seconds(), min_interval_seconds)
        for timeframe, duration in TIMEFRAME_DURATIONS.items()
    }
    for key, interval in (overrides or {}).items():
        try:
            # `Timeframe`'s values are lowercase (`"m1"`), but an
            # operator writing this config by hand will naturally type
            # `"M1"` - accept both rather than silently ignoring the
            # more likely spelling.
            timeframe = Timeframe(key.lower())
        except ValueError:
            logger.warning("market_data.unknown_timeframe_override", timeframe=key)
            continue
        if interval <= 0:
            logger.warning(
                "market_data.invalid_timeframe_override", timeframe=key, interval_seconds=interval
            )
            continue
        schedule[timeframe] = interval
    return schedule


#: Built from the configured floor at import time - this is what
#: `register_market_data_schedule` actually registers with Celery Beat.
BEAT_SCHEDULE_SECONDS: dict[Timeframe, float] = build_beat_schedule_seconds(
    settings.market_data_min_collection_interval_seconds,
    settings.market_data_collection_interval_overrides,
)

def lookback_for(timeframe: Timeframe) -> timedelta:
    """How far back one collection run fetches (ADR-171).

    `_LOOKBACK_INTERVALS` candles alone was only enough while each timeframe
    ran once per candle. On the 300s floor (ADR-140) M1 runs every five
    minutes, so a five-minute window left no overlap: the newest two minutes,
    not yet published by Twelve Data at each run, fell outside the next run's
    window and were never stored - about 40% of M1 candles. Spanning several
    runs fixes that at no quota cost: it is still one request per run."""
    by_candles = TIMEFRAME_DURATIONS[timeframe] * _LOOKBACK_INTERVALS
    by_runs = timedelta(seconds=BEAT_SCHEDULE_SECONDS[timeframe] * _LOOKBACK_RUNS)
    return max(by_candles, by_runs)


#: Seconds in a day - named rather than inlined as `86400` in the
#: projection arithmetic below.
_SECONDS_PER_DAY = 86_400


def projected_daily_requests_per_asset() -> float:
    """Sum of Beat runs/day across every timeframe, one request per asset
    per run (Phase 9H, ADR-140) - the same arithmetic that revealed the
    original cadence bug, kept as a real function so it can both be tested
    and reused for the startup warning below.

    Counts what Beat actually runs: a candle-close crontab (ADR-166, audit
    D9) runs once per listed minute of every listed hour, which for H4 is
    not the same as once per 4-hour interval."""
    total = 0.0
    for timeframe, interval in BEAT_SCHEDULE_SECONDS.items():
        schedule = schedule_for(timeframe, interval)
        if isinstance(schedule, crontab):
            total += len(schedule.hour) * len(schedule.minute)
        else:
            total += _SECONDS_PER_DAY / schedule
    return total


def log_quota_projection() -> None:
    """Startup-time recurrence guard (Phase 9H §4, ADR-140): this class of
    bug (a schedule that cannot fit its provider's documented daily cap) has
    now happened twice - here, and in news ingestion (`5ca5985`) - both set
    by cadence intuition rather than checked against the cap. Logs the
    projected daily request count for the *current* active-asset count
    against every provider that declares a daily limit, at WARNING if it
    would exceed that limit. Deliberately not a budget-aware scheduler -
    just a visible number an operator can act on."""
    session = SessionLocal()
    try:
        active_asset_count = len(AssetRepository(session).list_active(limit=1000))
    finally:
        session.close()

    per_asset = projected_daily_requests_per_asset()
    projected = per_asset * active_asset_count
    # ADR-182 - the swing paper pairs are inactive assets collected by their
    # own task, so they are not in `active_asset_count`; count them here.
    paper_requests = _PAPER_SWING_REQUESTS if settings.paper_swing_enabled else 0
    projected += paper_requests

    for provider_name, daily_limit in settings.market_data_rate_limits_per_day.items():
        if projected > daily_limit:
            logger.warning(
                "market_data.quota_projection_exceeds_limit",
                provider=provider_name,
                projected_requests_per_day=projected,
                daily_limit=daily_limit,
                active_asset_count=active_asset_count,
                requests_per_asset_per_day=per_asset,
                paper_swing_requests_per_day=paper_requests,
            )
        else:
            logger.info(
                "market_data.quota_projection",
                provider=provider_name,
                projected_requests_per_day=projected,
                daily_limit=daily_limit,
                active_asset_count=active_asset_count,
                requests_per_asset_per_day=per_asset,
                paper_swing_requests_per_day=paper_requests,
            )


@celery_app.task(name="market_data.collect_for_timeframe")  # type: ignore[untyped-decorator]
def collect_market_data_task(timeframe_value: str) -> None:
    """Single conceptual collection task, parameterized by timeframe
    (docs/38 §9). Celery Beat registers one schedule entry per `Timeframe`
    (see `register_market_data_schedule`), each invoking this same task
    with a different `timeframe_value` and interval - not a separate task
    per timeframe.

    Idempotent (docs/06 §16): re-running for an overlapping window is safe
    because `PriceCandleRepository.upsert` overwrites rather than
    duplicates.
    """
    timeframe = Timeframe(timeframe_value)
    session = SessionLocal()
    try:
        asset_repository = AssetRepository(session)
        service = MarketDataService(
            providers=get_market_data_providers(),
            candle_validator=CandleValidator(),
            price_candle_repository=PriceCandleRepository(session),
        )

        candle_repository = PriceCandleRepository(session)
        end = datetime.now(UTC)

        for asset in asset_repository.list_active(limit=1000):
            latest = candle_repository.get_latest(asset.id, timeframe)
            start = collection_start(
                timeframe, end, latest.timestamp if latest is not None else None
            )
            service.collect(asset, timeframe, start=start, end=end)

        session.commit()
    finally:
        session.close()


#: ADR-188 - the furthest one run reaches back to close a gap. 4,500 candles
#: stays under Twelve Data's 5,000-candle response (M1: ~3 days); 7 days caps
#: the higher timeframes, whose normal lookback already covers longer gaps.
_CATCH_UP_MAX_CANDLES = 4_500
_CATCH_UP_MAX_AGE = timedelta(days=7)


def collection_start(
    timeframe: Timeframe, end: datetime, latest_stored: datetime | None
) -> datetime:
    """Where one collection run starts fetching (ADR-171, ADR-188).

    Normally `end - lookback_for(timeframe)`. When the newest stored candle
    is older than that - the worker was down, the server was rebuilt from a
    backup, or the provider failed for a while - the run starts from that
    candle instead, so the gap closes on the next run rather than staying a
    permanent hole (2026-11-06: a day of H1 was missing after the restore and
    had to be backfilled by hand). Capped, so one run never asks for more than
    a provider returns. Still one request per run: no quota change."""
    normal_start = end - lookback_for(timeframe)
    if latest_stored is None:
        return normal_start
    cap = min(TIMEFRAME_DURATIONS[timeframe] * _CATCH_UP_MAX_CANDLES, _CATCH_UP_MAX_AGE)
    catch_up_start = max(as_aware_utc(latest_stored), end - cap)
    return min(normal_start, catch_up_start)


_FRESHNESS_COMPOSERS: dict[FreshnessAlert, Callable[..., str]] = {
    FreshnessAlert.STALE: compose_market_data_stale_message,
    FreshnessAlert.RESUMED: compose_market_data_resumed_message,
}


@celery_app.task(name="market_data.watch_freshness", ignore_result=True)  # type: ignore[untyped-decorator]
def watch_freshness_task() -> None:
    """ADR-188 - tells super admins when an active asset's prices stop, and
    when they resume. The decision is `services/market_data_watch.py`; this
    task loads, sends, and only then records - so a failed send is decided
    again, and retried, on the next run. Silently no-ops while Telegram is
    not configured."""
    if not credential_resolver.resolve("telegram_bot"):
        return

    session = SessionLocal()
    try:
        now = datetime.now(UTC)
        candles = PriceCandleRepository(session)
        telegram = TelegramService(
            account_repository=TelegramAccountRepository(session),
            provider=get_telegram_provider(),
        )
        for asset in AssetRepository(session).list_active(limit=1000):
            alerted = market_data_watch.is_alerted(asset.id)
            if alerted is None:
                continue
            latest = candles.get_latest(asset.id, Timeframe.M1)
            newest = latest.timestamp if latest is not None else None
            alert = market_data_watch.decide(newest, now, alerted=alerted)
            if alert is None:
                continue
            try:
                telegram.send_to_operators(
                    _FRESHNESS_COMPOSERS[alert](asset.symbol, newest, now=now)
                )
            except Exception:
                logger.warning(
                    "market_data.freshness_alert_failed", symbol=asset.symbol, exc_info=True
                )
                continue
            market_data_watch.record(asset.id, alert, now)
            logger.info("market_data.freshness_alerted", symbol=asset.symbol, alert=alert.value)
    finally:
        session.close()


def register_market_data_watch_schedule() -> dict[str, dict[str, object]]:
    return {
        "market-data-watch-freshness": {
            "task": "market_data.watch_freshness",
            "schedule": float(settings.market_data_watch_interval_seconds),
        }
    }


#: ADR-166 - H1 and M15 are collected on the clock, one minute after each
#: candle closes, so signal generation (minute 3) and M15 confirmation
#: (minutes 3, 18, 33, 48) read the candle that just closed. The same
#: number of runs per day as the intervals they replace, so the quota
#: projection above still holds.
_CANDLE_CLOSE_SCHEDULES: dict[Timeframe, crontab] = {
    Timeframe.H1: crontab(minute="1"),
    Timeframe.M15: crontab(minute="1,16,31,46"),
    #: Audit D9 (ADR-183) - the smc-ict-crt-v1 path decides on M5 and H4
    #: and may only use a candle fetched after its close plus Twelve Data's
    #: ~2-minute publication lag. On free-running intervals production
    #: first wrote M5 247 s into the candle and H4 44 minutes into it, and
    #: rewrote them only a run later, so every decision at the close read
    #: partial values. Minute 3 after the close is the first run that holds
    #: the final bar. M5: same 288 runs a day. H4: both the summer and the
    #: winter boundary hours (XAUUSD's H4 grid follows Twelve Data's day,
    #: which starts at 21:00 UTC in summer and 20:00 in winter - ADR-180),
    #: 12 runs a day instead of 6.
    Timeframe.M5: crontab(minute="3-58/5"),
    Timeframe.H4: crontab(minute="3", hour="0,1,4,5,8,9,12,13,16,17,20,21"),
}


def schedule_for(timeframe: Timeframe, interval_seconds: float) -> crontab | float:
    """The candle-close schedule where one exists, unless the operator
    overrode that timeframe or the floor raised its interval - both are
    deliberate choices this alignment must not silently undo."""
    aligned = _CANDLE_CLOSE_SCHEDULES.get(timeframe)
    overridden = {key.lower() for key in settings.market_data_collection_interval_overrides}
    if (
        aligned is None
        or timeframe.value in overridden
        or interval_seconds != TIMEFRAME_DURATIONS[timeframe].total_seconds()
    ):
        return interval_seconds
    return aligned


def register_market_data_schedule() -> dict[str, dict[str, object]]:
    """Build Celery Beat schedule entries - one per `Timeframe`, all
    invoking the same `collect_market_data_task` (docs/38 §9)."""
    return {
        f"collect-market-data-{timeframe.value}": {
            "task": "market_data.collect_for_timeframe",
            "schedule": schedule_for(timeframe, interval_seconds),
            "args": (timeframe.value,),
        }
        for timeframe, interval_seconds in BEAT_SCHEDULE_SECONDS.items()
    }
