from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import Timeframe
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.normalization import NormalizedCandle, normalize_candle
from app.services.market_data.providers.base import RawCandle


def _candle(**overrides: object) -> NormalizedCandle:
    defaults: dict[str, object] = {
        "symbol": "EURUSD",
        "timeframe": Timeframe.M1,
        "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
        "open": Decimal("1.1"),
        "high": Decimal("1.2"),
        "low": Decimal("1.0"),
        "close": Decimal("1.15"),
        "volume": Decimal("100"),
    }
    defaults.update(overrides)
    return NormalizedCandle(**defaults)  # type: ignore[arg-type]


def test_valid_candle_passes() -> None:
    is_valid, reason = CandleValidator().validate(_candle())
    assert is_valid is True
    assert reason is None


def test_rejects_non_positive_price() -> None:
    is_valid, reason = CandleValidator().validate(_candle(open=Decimal("0")))
    assert is_valid is False
    assert reason == "non_positive_price"


def test_rejects_high_less_than_low() -> None:
    is_valid, reason = CandleValidator().validate(_candle(high=Decimal("0.5"), low=Decimal("1.0")))
    assert is_valid is False
    assert reason == "high_less_than_low"


def test_rejects_high_below_close() -> None:
    is_valid, reason = CandleValidator().validate(
        _candle(high=Decimal("1.05"), close=Decimal("1.15"))
    )
    assert is_valid is False
    assert reason == "high_below_open_or_close"


def test_rejects_low_above_open() -> None:
    is_valid, reason = CandleValidator().validate(_candle(low=Decimal("1.12"), open=Decimal("1.1")))
    assert is_valid is False
    assert reason == "low_above_open_or_close"


def test_rejects_negative_volume() -> None:
    is_valid, reason = CandleValidator().validate(_candle(volume=Decimal("-1")))
    assert is_valid is False
    assert reason == "negative_volume"


def test_accepts_null_volume() -> None:
    is_valid, reason = CandleValidator().validate(_candle(volume=None))
    assert is_valid is True
    assert reason is None


def test_normalize_candle_converts_naive_timestamp_to_utc_aware() -> None:
    raw = RawCandle(
        symbol="EURUSD",
        timeframe=Timeframe.M1,
        timestamp=datetime(2026, 1, 1, 12, 0, 0),  # naive
        open=1.1,
        high=1.2,
        low=1.0,
        close=1.15,
        volume=100.0,
    )
    normalized = normalize_candle(raw)
    assert normalized.timestamp.tzinfo is not None
    assert normalized.open == Decimal("1.1")
    assert normalized.volume == Decimal("100.0")


def test_normalize_candle_handles_null_volume() -> None:
    raw = RawCandle(
        symbol="EURUSD",
        timeframe=Timeframe.M1,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        open=1.1,
        high=1.2,
        low=1.0,
        close=1.15,
        volume=None,
    )
    assert normalize_candle(raw).volume is None
