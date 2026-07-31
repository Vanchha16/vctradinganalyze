from app.models.enums import Timeframe
from app.services.market_data.providers.twelve_data_symbols import (
    from_provider_symbol,
    timeframe_to_interval,
    to_provider_symbol,
)


def test_to_provider_symbol_splits_forex_pair() -> None:
    assert to_provider_symbol("EURUSD") == "EUR/USD"
    assert to_provider_symbol("GBPUSD") == "GBP/USD"


def test_to_provider_symbol_splits_metal_pair() -> None:
    assert to_provider_symbol("XAUUSD") == "XAU/USD"


def test_to_provider_symbol_splits_crypto_pair() -> None:
    assert to_provider_symbol("BTCUSD") == "BTC/USD"


def test_to_provider_symbol_returns_none_for_short_index_symbol() -> None:
    assert to_provider_symbol("US30") is None


def test_to_provider_symbol_does_not_misinterpret_six_character_index_symbol() -> None:
    """NAS100 is also 6 characters, like EURUSD - the mechanical rule must
    not blindly split any 6-character symbol, or this would wrongly
    produce "NAS/100" instead of correctly failing (docs/41 §3 note)."""
    assert to_provider_symbol("NAS100") is None


def test_to_provider_symbol_returns_none_for_unrecognized_pair() -> None:
    assert to_provider_symbol("ZZZQQQ") is None


def test_from_provider_symbol_strips_delimiter() -> None:
    assert from_provider_symbol("EUR/USD") == "EURUSD"


def test_timeframe_to_interval_covers_every_canonical_timeframe() -> None:
    expected = {
        Timeframe.M1: "1min",
        Timeframe.M5: "5min",
        Timeframe.M15: "15min",
        Timeframe.M30: "30min",
        Timeframe.H1: "1h",
        Timeframe.H4: "4h",
        Timeframe.D1: "1day",
        Timeframe.W1: "1week",
        Timeframe.MN: "1month",
    }
    for timeframe, interval in expected.items():
        assert timeframe_to_interval(timeframe) == interval
