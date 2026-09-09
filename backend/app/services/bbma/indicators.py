"""Series-valued indicators BBMA needs (docs/61, ADR-148).

The existing `app/indicators/` functions return only the **latest** value
- correct for scoring a snapshot, useless for BBMA, which has to look
back across candles to find an Extreme, then its reverse candle, then its
retest. These return the full aligned series instead.

`None` at index `i` means "not enough history yet at that bar". Every
series returned here is the same length as its input, so indices line up
with the candle series and callers never have to offset.
"""

from app.indicators._utils import population_stdev, sma


def wma_series(values: list[float], period: int) -> list[float | None]:
    """Linear Weighted Moving Average, the `MA method: Linear Weighted`
    of MT4/MT5 (docs/61 §1).

    Weights rise linearly toward the most recent bar: the newest value
    carries weight `period`, the oldest in the window carries 1. This is
    **not** an EMA and not an SMA - BBMA's MA5/MA10 entry bands depend on
    this exact weighting, so it is implemented here rather than
    approximated with something already in `app/indicators/`.
    """
    if period <= 0:
        raise ValueError("period must be positive")

    weights = list(range(1, period + 1))
    weight_total = float(sum(weights))
    out: list[float | None] = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        out[i] = sum(v * w for v, w in zip(window, weights, strict=True)) / weight_total
    return out


def bollinger_series(
    closes: list[float], period: int = 20, std_dev_multiplier: float = 2.0
) -> list[tuple[float, float, float] | None]:
    """(upper, middle, lower) per bar. Mid BB is SMA(period) - docs/61 §1.

    Deliberately mirrors `app.indicators.volatility.bollinger_bands`'
    maths (same `sma`, same `population_stdev`) so the two can never
    disagree about where a band sits; only the shape of the output
    differs.
    """
    out: list[tuple[float, float, float] | None] = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        middle = sma(window, period)
        if middle is None:  # pragma: no cover - window is exactly `period`
            continue
        std = population_stdev(window)
        out[i] = (
            middle + std_dev_multiplier * std,
            middle,
            middle - std_dev_multiplier * std,
        )
    return out


def ema_series(values: list[float], period: int) -> list[float | None]:
    """EMA per bar, for the EMA50 trend major (docs/61 §2.2).

    `app.indicators._utils.ema_full` already does this; re-exported
    through this module so BBMA has one import site for its series
    indicators rather than reaching into two packages.
    """
    from app.indicators._utils import ema_full

    return ema_full(values, period)


__all__ = ["bollinger_series", "ema_series", "wma_series"]
