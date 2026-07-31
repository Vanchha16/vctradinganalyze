from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OHLCVSeries:
    """A chronologically-ordered (oldest first) OHLCV series, the common
    input every indicator function takes."""

    opens: list[float]
    highs: list[float]
    lows: list[float]
    closes: list[float]
    volumes: list[float | None]


@dataclass(frozen=True, slots=True)
class IndicatorOutput:
    """An indicator's computed result: a headline `value` (stored in
    `IndicatorResult.value`) plus optional secondary values (stored in
    `IndicatorResult.context`/`metadata`) for multi-output indicators like
    MACD, Bollinger Bands, and ADX."""

    value: float
    metadata: dict[str, float] | None = None
