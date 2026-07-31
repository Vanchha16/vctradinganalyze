from app.services.market_data.normalization import NormalizedCandle


class CandleValidator:
    """Validates a normalized candle before persistence (docs/08 §12,
    docs/38 §5). `MarketDataService` orchestrates the collection workflow;
    this component owns the validation rules exclusively."""

    def validate(self, candle: NormalizedCandle) -> tuple[bool, str | None]:
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
        return True, None
