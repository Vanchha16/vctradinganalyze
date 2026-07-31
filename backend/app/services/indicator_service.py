import uuid

import structlog

from app.indicators import OHLCVSeries, registry
from app.models.enums import Timeframe
from app.models.indicator_result import IndicatorResult
from app.repositories.indicator_result_repository import IndicatorResultRepository
from app.repositories.price_candle_repository import PriceCandleRepository

logger = structlog.get_logger(__name__)

_DEFAULT_LOOKBACK = 500


class IndicatorService:
    """Populates `indicator_results` with raw indicator values (docs/38 §1).

    Deliberately does not perform trend detection, technical scoring, or
    conflict detection (docs/08 §7-11) - that synthesis is Phase 4's
    Technical Analysis Engine, consuming what this service persists.
    """

    def __init__(
        self,
        price_candle_repository: PriceCandleRepository,
        indicator_result_repository: IndicatorResultRepository,
    ) -> None:
        self._price_candle_repository = price_candle_repository
        self._indicator_result_repository = indicator_result_repository

    def calculate_and_store(
        self, asset_id: uuid.UUID, timeframe: Timeframe, *, lookback: int = _DEFAULT_LOOKBACK
    ) -> list[IndicatorResult]:
        candles = self._price_candle_repository.list_recent(asset_id, timeframe, limit=lookback)
        if not candles:
            return []

        series = OHLCVSeries(
            opens=[float(c.open) for c in candles],
            highs=[float(c.high) for c in candles],
            lows=[float(c.low) for c in candles],
            closes=[float(c.close) for c in candles],
            volumes=[float(c.volume) if c.volume is not None else None for c in candles],
        )

        results: list[IndicatorResult] = []
        for spec in registry.list_all():
            output = spec.func(series)
            if output is None:
                logger.debug(
                    "indicators.insufficient_data",
                    indicator=spec.name,
                    asset_id=str(asset_id),
                    timeframe=timeframe.value,
                )
                continue

            result = IndicatorResult(
                asset_id=asset_id,
                timeframe=timeframe,
                indicator=spec.name,
                value=output.value,
                context=output.metadata,
            )
            self._indicator_result_repository.create(result)
            results.append(result)

        logger.info(
            "indicators.calculated",
            asset_id=str(asset_id),
            timeframe=timeframe.value,
            count=len(results),
        )
        return results
