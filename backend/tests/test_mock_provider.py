from datetime import UTC, datetime, timedelta

from app.models.enums import Timeframe
from app.services.market_data.providers.mock import MockMarketDataProvider


def test_mock_provider_is_deterministic_across_instances() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(minutes=10)

    first = MockMarketDataProvider().get_candles("EURUSD", Timeframe.M1, start, end)
    second = MockMarketDataProvider().get_candles("EURUSD", Timeframe.M1, start, end)

    assert [c.close for c in first] == [c.close for c in second]


def test_mock_provider_differs_per_symbol() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(minutes=10)

    eurusd = MockMarketDataProvider().get_candles("EURUSD", Timeframe.M1, start, end)
    gbpusd = MockMarketDataProvider().get_candles("GBPUSD", Timeframe.M1, start, end)

    assert [c.close for c in eurusd] != [c.close for c in gbpusd]


def test_mock_provider_generates_valid_ohlc_relationships() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(hours=1)

    candles = MockMarketDataProvider().get_candles("XAUUSD", Timeframe.M5, start, end)

    assert len(candles) > 1
    for candle in candles:
        assert candle.high >= candle.open
        assert candle.high >= candle.close
        assert candle.low <= candle.open
        assert candle.low <= candle.close
        assert candle.volume is not None
        assert candle.volume > 0


def test_mock_provider_health_check_always_true() -> None:
    assert MockMarketDataProvider().health_check() is True
