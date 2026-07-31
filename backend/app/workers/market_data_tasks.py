from datetime import UTC, datetime

from app.database.session import SessionLocal
from app.dependencies.market_data import get_market_data_providers
from app.models.enums import Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.timeframe_utils import TIMEFRAME_DURATIONS
from app.services.market_data_service import MarketDataService
from app.workers.celery_app import celery_app

# A small lookback multiplier so a run that's late (or a missed tick) still
# catches up on the intervening candles - the collection itself is
# idempotent (PriceCandleRepository.upsert), so re-fetching overlap is safe.
_LOOKBACK_INTERVALS = 5

#: Celery Beat interval (seconds) per timeframe - shorter timeframes are
#: polled more often, matching how often a new candle actually forms.
BEAT_SCHEDULE_SECONDS: dict[Timeframe, float] = {
    timeframe: duration.total_seconds() for timeframe, duration in TIMEFRAME_DURATIONS.items()
}


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
