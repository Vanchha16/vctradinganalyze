from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies.database import get_db
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.providers.base import MarketDataProvider
from app.services.market_data.providers.mock import MockMarketDataProvider
from app.services.market_data_service import MarketDataService

_PROVIDER_FACTORIES: dict[str, Callable[[], MarketDataProvider]] = {
    "mock": MockMarketDataProvider,
}


def get_market_data_providers() -> list[MarketDataProvider]:
    """Build the configured provider chain (docs/38 §10).

    This is the only place that knows concrete provider classes exist -
    everything above it depends on the `MarketDataProvider` interface.
    Adding a provider means adding it to `_PROVIDER_FACTORIES` and to
    `settings.market_data_providers`, without touching `MarketDataService`.
    """
    providers: list[MarketDataProvider] = []
    for name in settings.market_data_providers:
        factory = _PROVIDER_FACTORIES.get(name)
        if factory is None:
            raise ValueError(f"Unknown market data provider configured: {name!r}")
        providers.append(factory())
    return providers


def get_market_data_service(db: Annotated[Session, Depends(get_db)]) -> MarketDataService:
    return MarketDataService(
        providers=get_market_data_providers(),
        candle_validator=CandleValidator(),
        price_candle_repository=PriceCandleRepository(db),
    )
