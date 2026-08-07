from datetime import UTC, datetime

import structlog

from app.config import settings
from app.database.session import SessionLocal
from app.dependencies.market_data import get_market_data_providers
from app.models.enums import Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.timeframe_utils import TIMEFRAME_DURATIONS
from app.services.market_data_service import MarketDataService
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

# A small lookback multiplier so a run that's late (or a missed tick) still
# catches up on the intervening candles - the collection itself is
# idempotent (PriceCandleRepository.upsert), so re-fetching overlap is safe.
_LOOKBACK_INTERVALS = 5


def build_beat_schedule_seconds(min_interval_seconds: float) -> dict[Timeframe, float]:
    """Celery Beat interval (seconds) per timeframe - shorter timeframes are
    polled more often, matching how often a new candle actually forms, but
    never more often than `min_interval_seconds` (Phase 9H, ADR-140) -
    timeframes already longer than the floor are unaffected by `max()`
    here. A plain function, not just a module-level dict comprehension, so
    the floor's effect on the schedule is directly testable without
    reimporting the module for a different setting value."""
    return {
        timeframe: max(duration.total_seconds(), min_interval_seconds)
        for timeframe, duration in TIMEFRAME_DURATIONS.items()
    }


#: Built from the configured floor at import time - this is what
#: `register_market_data_schedule` actually registers with Celery Beat.
BEAT_SCHEDULE_SECONDS: dict[Timeframe, float] = build_beat_schedule_seconds(
    settings.market_data_min_collection_interval_seconds
)

#: Seconds in a day - named rather than inlined as `86400` in the
#: projection arithmetic below.
_SECONDS_PER_DAY = 86_400


def projected_daily_requests_per_asset() -> float:
    """Sum of Beat runs/day across every timeframe, one request per asset
    per run (Phase 9H, ADR-140) - the same arithmetic that revealed the
    original cadence bug, kept as a real function so it can both be tested
    and reused for the startup warning below."""
    return sum(_SECONDS_PER_DAY / interval for interval in BEAT_SCHEDULE_SECONDS.values())


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

    for provider_name, daily_limit in settings.market_data_rate_limits_per_day.items():
        if projected > daily_limit:
            logger.warning(
                "market_data.quota_projection_exceeds_limit",
                provider=provider_name,
                projected_requests_per_day=projected,
                daily_limit=daily_limit,
                active_asset_count=active_asset_count,
                requests_per_asset_per_day=per_asset,
            )
        else:
            logger.info(
                "market_data.quota_projection",
                provider=provider_name,
                projected_requests_per_day=projected,
                daily_limit=daily_limit,
                active_asset_count=active_asset_count,
                requests_per_asset_per_day=per_asset,
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

        end = datetime.now(UTC)
        start = end - TIMEFRAME_DURATIONS[timeframe] * _LOOKBACK_INTERVALS

        for asset in asset_repository.list_active(limit=1000):
            service.collect(asset, timeframe, start=start, end=end)

        session.commit()
    finally:
        session.close()


def register_market_data_schedule() -> dict[str, dict[str, object]]:
    """Build Celery Beat schedule entries - one per `Timeframe`, all
    invoking the same `collect_market_data_task` (docs/38 §9)."""
    return {
        f"collect-market-data-{timeframe.value}": {
            "task": "market_data.collect_for_timeframe",
            "schedule": interval_seconds,
            "args": (timeframe.value,),
        }
        for timeframe, interval_seconds in BEAT_SCHEDULE_SECONDS.items()
    }
