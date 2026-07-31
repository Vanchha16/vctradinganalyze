from enum import StrEnum


class Timeframe(StrEnum):
    """Candle timeframes, per docs/08_TECHNICAL_ANALYSIS_ENGINE.md §4."""

    M1 = "m1"
    M5 = "m5"
    M15 = "m15"
    M30 = "m30"
    H1 = "h1"
    H4 = "h4"
    D1 = "d1"
    W1 = "w1"
    MN = "mn"
