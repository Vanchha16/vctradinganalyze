import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import structlog

from app.config import settings
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.models.price_candle import PriceCandle
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.exceptions import MarketDataProviderError, TransientProviderError
from app.services.market_data.normalization import normalize_candle
from app.services.market_data.providers.base import MarketDataProvider, RawCandle

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class CollectionResult:
    fetched: int
    persisted: int
    rejected: int


class MarketDataService:
    """Orchestrates candle collection: fetch (with retry/failover across
    providers) -> normalize -> validate -> persist.

    Validation itself lives entirely in `CandleValidator` (docs/38 §5) -
    this service coordinates the workflow, it does not decide what makes a
    candle valid. Likewise, rate limiting is applied to providers before
    they reach this service (`RateLimitedProvider`, docs/40) - this class
    has no rate-limiting logic of its own and stays provider-agnostic.
    """

    def __init__(
        self,
        providers: list[MarketDataProvider],
        candle_validator: CandleValidator,
        price_candle_repository: PriceCandleRepository,
        *,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._providers = providers
        self._candle_validator = candle_validator
        self._price_candle_repository = price_candle_repository
        self._sleep = sleep
        self._clock = clock

    def collect(
        self, asset: Asset, timeframe: Timeframe, *, start: datetime, end: datetime
    ) -> CollectionResult:
        raw_candles = self._fetch_with_failover(asset, timeframe, start, end)

        persisted = 0
        rejected = 0
        for raw in raw_candles:
            normalized = normalize_candle(raw)
            is_valid, reason = self._candle_validator.validate(
                normalized, window_start=start, window_end=end
            )
            if not is_valid:
                rejected += 1
                logger.warning(
                    "market_data.candle_rejected",
                    asset=asset.symbol,
                    timeframe=timeframe.value,
                    timestamp=str(normalized.timestamp),
                    reason=reason,
                )
                continue

            candle = PriceCandle(
                asset_id=asset.id,
                timeframe=timeframe,
                timestamp=normalized.timestamp,
                open=normalized.open,
                high=normalized.high,
                low=normalized.low,
                close=normalized.close,
                volume=normalized.volume,
            )
            self._price_candle_repository.upsert(candle)
            persisted += 1

        logger.info(
            "market_data.collected",
            asset=asset.symbol,
            timeframe=timeframe.value,
            fetched=len(raw_candles),
            persisted=persisted,
            rejected=rejected,
        )
        return CollectionResult(fetched=len(raw_candles), persisted=persisted, rejected=rejected)

    def _fetch_with_failover(
        self, asset: Asset, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        for provider in self._providers:
            if not provider.capabilities().supports(timeframe, market_type=asset.market_type):
                logger.warning(
                    "market_data.provider_unsupported",
                    provider=provider.name,
                    symbol=asset.symbol,
                    timeframe=timeframe.value,
                )
                continue

            try:
                return self._fetch_with_retry(provider, asset.symbol, timeframe, start, end)
            except MarketDataProviderError as exc:
                logger.warning(
                    "market_data.provider_failed",
                    provider=provider.name,
                    symbol=asset.symbol,
                    timeframe=timeframe.value,
                    error=str(exc),
                )
                continue

        logger.error(
            "market_data.all_providers_failed", symbol=asset.symbol, timeframe=timeframe.value
        )
        # Every provider failed (or none support this timeframe/market
        # type): fall back to whatever is already stored (docs/38 §8) by
        # simply fetching nothing new - existing price_candles rows are
        # left untouched, not deleted.
        return []

    def _fetch_with_retry(
        self,
        provider: MarketDataProvider,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[RawCandle]:
        attempt = 0
        while True:
            attempt += 1
            call_start = self._clock()
            try:
                candles = provider.get_candles(symbol, timeframe, start, end)
            except MarketDataProviderError as exc:
                duration_ms = round((self._clock() - call_start) * 1000, 2)
                is_transient = isinstance(exc, TransientProviderError)
                logger.warning(
                    "market_data.provider_call",
                    provider=provider.name,
                    symbol=symbol,
                    timeframe=timeframe.value,
                    duration_ms=duration_ms,
                    outcome="transient_error" if is_transient else "permanent_error",
                    attempt=attempt,
                )
                if not is_transient or attempt >= settings.market_data_retry_max_attempts:
                    raise
                self._sleep(settings.market_data_retry_backoff_seconds * attempt)
                continue

            logger.info(
                "market_data.provider_call",
                provider=provider.name,
                symbol=symbol,
                timeframe=timeframe.value,
                duration_ms=round((self._clock() - call_start) * 1000, 2),
                outcome="success",
                attempt=attempt,
                candle_count=len(candles),
            )
            return candles
