from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies.database import get_db
from app.repositories.asset_repository import AssetRepository
from app.repositories.indicator_result_repository import IndicatorResultRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.exceptions import ProviderConfigurationError
from app.services.market_data.providers.base import MarketDataProvider
from app.services.market_data.providers.mock import MockMarketDataProvider
from app.services.market_data.providers.rate_limited import RateLimitedProvider
from app.services.market_data.providers.twelve_data import TwelveDataProvider
from app.services.market_data_service import MarketDataService


def _build_twelve_data_provider() -> MarketDataProvider:
    if not settings.twelve_data_api_key:
        raise ProviderConfigurationError(
            "twelve_data is configured in market_data_providers but "
            "TWELVE_DATA_API_KEY is not set (docs/40 §8)"
        )
    return TwelveDataProvider(
        api_key=settings.twelve_data_api_key,
        base_url=settings.twelve_data_base_url,
        timeout=settings.twelve_data_timeout_seconds,
    )


_PROVIDER_FACTORIES: dict[str, Callable[[], MarketDataProvider]] = {
    "mock": MockMarketDataProvider,
    "twelve_data": _build_twelve_data_provider,
}


def get_market_data_providers() -> list[MarketDataProvider]:
    """Build the configured provider chain (docs/38 §10, docs/40).

    This is the only place that knows concrete provider classes exist -
    everything above it depends on the `MarketDataProvider` interface.
    Adding a provider means adding it to `_PROVIDER_FACTORIES`, to
    `settings.market_data_providers`, and (optionally) to
    `settings.market_data_rate_limits_per_minute`/`..._per_day` - without
    touching `MarketDataService`. Every provider is wrapped in
    `RateLimitedProvider` here, so rate limiting is applied uniformly
    without any provider implementation needing to know about it.
    """
    providers: list[MarketDataProvider] = []
    for name in settings.market_data_providers:
        factory = _PROVIDER_FACTORIES.get(name)
        if factory is None:
            raise ProviderConfigurationError(f"Unknown market data provider configured: {name!r}")

        rate_limit = settings.market_data_rate_limits_per_minute.get(
            name, settings.market_data_default_rate_limit_per_minute
        )
        daily_limit = settings.market_data_rate_limits_per_day.get(
            name, settings.market_data_default_rate_limit_per_day
        )
        providers.append(RateLimitedProvider(factory(), rate_limit, requests_per_day=daily_limit))
    return providers


def get_market_data_service(db: Annotated[Session, Depends(get_db)]) -> MarketDataService:
    return MarketDataService(
        providers=get_market_data_providers(),
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(db),
    )


def get_asset_repository(db: Annotated[Session, Depends(get_db)]) -> AssetRepository:
    return AssetRepository(db)


def get_price_candle_repository(
    db: Annotated[Session, Depends(get_db)],
) -> PriceCandleRepository:
    return PriceCandleRepository(db)


def get_indicator_result_repository(
    db: Annotated[Session, Depends(get_db)],
) -> IndicatorResultRepository:
    return IndicatorResultRepository(db)
