from typing import Protocol

from app.models.enums import Timeframe


class MarketDataScheduler(Protocol):
    """Contract for triggering periodic market-data collection.

    Collection is treated conceptually as a single operation parameterized
    by timeframe (docs/38 §9) - a concrete implementation (Celery Beat, see
    `app/workers/market_data_tasks.py`) may need multiple schedule entries
    under the hood (one per `Timeframe`, each with its own interval), but
    every entry invokes this same underlying operation.
    """

    def collect_for_timeframe(self, timeframe: Timeframe) -> None: ...
