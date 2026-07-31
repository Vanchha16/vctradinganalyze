"""docs/08 §6 Support & Resistance (docs/42 §10, ADR-029):

- Swing highs/lows via classic fractal detection.
- Daily/weekly/monthly highs/lows, aggregated from D1 candles
  specifically - independent of the requested analysis timeframe.
- Round numbers / psychological levels via a magnitude-aware rounding
  heuristic (proportional step size), not a hardcoded per-symbol table.
"""

from collections.abc import Sequence
from decimal import ROUND_FLOOR, Decimal

from app.models.price_candle import PriceCandle
from app.services.technical_analysis.types import SupportResistanceEvidence, SupportResistanceLevel

#: Candles on each side of a candidate swing point (classic 5-candle fractal).
_FRACTAL_WINDOW = 2
_LEVELS_TO_KEEP = 5


def _find_swing_points(
    candles: Sequence[PriceCandle],
) -> tuple[list[SupportResistanceLevel], list[SupportResistanceLevel]]:
    highs: list[SupportResistanceLevel] = []
    lows: list[SupportResistanceLevel] = []
    n = len(candles)

    for i in range(_FRACTAL_WINDOW, n - _FRACTAL_WINDOW):
        window = candles[i - _FRACTAL_WINDOW : i + _FRACTAL_WINDOW + 1]
        candle = candles[i]
        if candle.high == max(c.high for c in window):
            highs.append(
                SupportResistanceLevel(price=candle.high, source="swing_high", strength="weak")
            )
        if candle.low == min(c.low for c in window):
            lows.append(
                SupportResistanceLevel(price=candle.low, source="swing_low", strength="weak")
            )

    return highs, lows


def _period_high_low(
    daily_candles: Sequence[PriceCandle], days: int, source_prefix: str
) -> tuple[SupportResistanceLevel | None, SupportResistanceLevel | None]:
    window = daily_candles[-days:]
    if not window:
        return None, None

    high = max(c.high for c in window)
    low = min(c.low for c in window)
    return (
        SupportResistanceLevel(price=high, source=f"{source_prefix}_high", strength="moderate"),
        SupportResistanceLevel(price=low, source=f"{source_prefix}_low", strength="moderate"),
    )


def _round_number_levels(current_price: Decimal) -> list[SupportResistanceLevel]:
    """Magnitude-aware rounding heuristic (ADR-029) - a step size
    proportional to the current price's order of magnitude, e.g. ~0.005
    for a ~1.10 forex pair, ~100 for a ~2400 gold/index price - rather
    than a hardcoded per-symbol table that wouldn't generalize to new
    assets."""
    if current_price <= 0:
        return []

    magnitude = current_price.log10().to_integral_value(rounding=ROUND_FLOOR)
    step = (Decimal(10) ** magnitude) / 20
    if step <= 0:
        return []

    lower = (current_price / step).to_integral_value(rounding=ROUND_FLOOR) * step
    upper = lower + step

    levels = [SupportResistanceLevel(price=upper, source="round_number", strength="weak")]
    if lower > 0:
        levels.append(SupportResistanceLevel(price=lower, source="round_number", strength="weak"))
    return levels


def analyze(
    recent_candles: Sequence[PriceCandle],
    daily_candles: Sequence[PriceCandle],
    current_price: Decimal,
) -> SupportResistanceEvidence:
    swing_highs, swing_lows = _find_swing_points(recent_candles)

    daily_high, daily_low = _period_high_low(daily_candles, 1, "daily")
    weekly_high, weekly_low = _period_high_low(daily_candles, 7, "weekly")
    monthly_high, monthly_low = _period_high_low(daily_candles, 30, "monthly")

    round_levels = _round_number_levels(current_price)

    candidate_highs = [
        level
        for level in (daily_high, weekly_high, monthly_high, *swing_highs, *round_levels)
        if level is not None and level.price > current_price
    ]
    candidate_lows = [
        level
        for level in (daily_low, weekly_low, monthly_low, *swing_lows, *round_levels)
        if level is not None and level.price < current_price
    ]

    candidate_highs.sort(key=lambda level: level.price)
    candidate_lows.sort(key=lambda level: level.price, reverse=True)

    return SupportResistanceEvidence(
        nearest_support=candidate_lows[0] if candidate_lows else None,
        nearest_resistance=candidate_highs[0] if candidate_highs else None,
        support_levels=candidate_lows[:_LEVELS_TO_KEEP],
        resistance_levels=candidate_highs[:_LEVELS_TO_KEEP],
    )
