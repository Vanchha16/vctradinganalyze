"""Shared contract-test helper for `MarketDataProvider` implementations (docs/40).

Every future provider's test suite (Phase 3B onward) should call
`assert_provider_contract` against that provider - using a real or
recorded response - to confirm it honors the same structural guarantees
`MarketDataService` depends on, independent of the provider's specific
data. See `test_mock_provider.py` for the reference usage against
`MockMarketDataProvider`.

Not named `test_*.py` so pytest does not try to collect this module as a
test suite itself - it is a helper, imported by provider-specific tests.
"""

from datetime import datetime

from app.models.enums import Timeframe
from app.services.market_data.providers.base import MarketDataProvider


def assert_provider_contract(
    provider: MarketDataProvider,
    symbol: str,
    timeframe: Timeframe,
    start: datetime,
    end: datetime,
) -> None:
    assert provider.name, "MarketDataProvider.name must be non-empty"

    capabilities = provider.capabilities()
    assert timeframe in capabilities.supported_timeframes, (
        f"{provider.name} does not declare support for {timeframe} - "
        "only call this contract test with a timeframe capabilities() claims to support"
    )

    candles = provider.get_candles(symbol, timeframe, start, end)
    for candle in candles:
        assert candle.symbol == symbol
        assert candle.timeframe == timeframe
        assert candle.open > 0
        assert candle.high > 0
        assert candle.low > 0
        assert candle.close > 0
        assert candle.high >= candle.low
        assert candle.high >= candle.open
        assert candle.high >= candle.close
        assert candle.low <= candle.open
        assert candle.low <= candle.close
        if candle.volume is not None:
            assert candle.volume >= 0
