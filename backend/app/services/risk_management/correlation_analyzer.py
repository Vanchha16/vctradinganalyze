"""Deterministic correlation analysis (docs/12 §9, docs/48 §5, ADR-067).
Real Pearson correlation of close-price returns, computed only for a
fixed curated pair list matching docs/12 §9's own named examples - never
a hard reject (this project has no portfolio/position tracking to know
whether the caller is actually exposed to both assets)."""

from decimal import Decimal

_CORRELATION_THRESHOLD = 0.85

# docs/12 §9's own named examples - a fixed, curated list, not a
# market-wide correlation model (ADR-067).
CURATED_PAIRS: dict[str, tuple[str, ...]] = {
    "EURUSD": ("GBPUSD",),
    "GBPUSD": ("EURUSD",),
    "XAUUSD": ("XAGUSD",),
    "XAGUSD": ("XAUUSD",),
    "BTCUSD": ("ETHUSD",),
    "ETHUSD": ("BTCUSD",),
}


def counterparts_for(symbol: str) -> tuple[str, ...]:
    return CURATED_PAIRS.get(symbol.upper(), ())


def _returns(series: list[Decimal]) -> list[float]:
    values = [float(v) for v in series]
    return [
        (values[i] - values[i - 1]) / values[i - 1] if values[i - 1] != 0 else 0.0
        for i in range(1, len(values))
    ]


def pearson_correlation(series_a: list[Decimal], series_b: list[Decimal]) -> float | None:
    """Pearson correlation of the two series' returns (not raw closes,
    to avoid trivial correlation from shared scale/trend). `None` if
    either series is too short or has zero variance."""
    if len(series_a) < 2 or len(series_b) < 2:
        return None

    length = min(len(series_a), len(series_b))
    returns_a = _returns(series_a[-length:])
    returns_b = _returns(series_b[-length:])
    n = min(len(returns_a), len(returns_b))
    if n < 2:
        return None
    returns_a, returns_b = returns_a[-n:], returns_b[-n:]

    mean_a = sum(returns_a) / n
    mean_b = sum(returns_b) / n
    covariance = sum((a - mean_a) * (b - mean_b) for a, b in zip(returns_a, returns_b, strict=True))
    variance_a = sum((a - mean_a) ** 2 for a in returns_a)
    variance_b = sum((b - mean_b) ** 2 for b in returns_b)

    denominator = (variance_a * variance_b) ** 0.5
    if denominator == 0:
        return None
    return float(covariance / denominator)


def is_highly_correlated(correlation: float | None) -> bool:
    return correlation is not None and abs(correlation) > _CORRELATION_THRESHOLD
