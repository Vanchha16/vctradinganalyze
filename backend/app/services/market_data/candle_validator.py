from datetime import datetime, timedelta

from app.services.market_data.normalization import NormalizedCandle

_DEFAULT_CLOCK_SKEW_TOLERANCE = timedelta(minutes=1)


class CandleValidator:
    """Validates a normalized candle before persistence (docs/08 §12,
    docs/34 "Validation", docs/38 §5). `MarketDataService` orchestrates the
    collection workflow; this component owns the validation rules
    exclusively."""

    def __init__(self, *, clock_skew_tolerance: timedelta = _DEFAULT_CLOCK_SKEW_TOLERANCE) -> None:
        self._clock_skew_tolerance = clock_skew_tolerance

    def validate(
        self,
        candle: NormalizedCandle,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> tuple[bool, str | None]:
        if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
            return False, "non_positive_price"
        if candle.high < candle.low:
            return False, "high_less_than_low"
        if candle.high < candle.open or candle.high < candle.close:
            return False, "high_below_open_or_close"
        if candle.low > candle.open or candle.low > candle.close:
            return False, "low_above_open_or_close"
        if candle.volume is not None and candle.volume < 0:
            return False, "negative_volume"

        if candle.timestamp < window_start - self._clock_skew_tolerance:
            return False, "timestamp_before_requested_window"
        if candle.timestamp > window_end + self._clock_skew_tolerance:
            return False, "timestamp_after_requested_window"

        return True, None
