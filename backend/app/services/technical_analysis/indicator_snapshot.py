"""Computes every registered indicator once against a candle series
(docs/39), for the Technical Analysis Engine to interpret. Reuses the
Phase 3A indicator registry directly rather than reading persisted
`indicator_results` rows, to avoid staleness between Celery Beat
collection cycles (docs/42 §2)."""

from app.indicators import OHLCVSeries, registry
from app.indicators.types import IndicatorOutput


def compute_indicator_snapshot(
    series: OHLCVSeries,
) -> tuple[dict[str, IndicatorOutput], list[str]]:
    """Returns (values_by_indicator_name, warnings).

    An indicator returning `None` (insufficient warm-up history, docs/39
    §7) is omitted and recorded as a warning rather than treated as fatal
    - distinct from docs/08 §12's "reject on missing candles," which the
    caller enforces separately before this is ever called.
    """
    values: dict[str, IndicatorOutput] = {}
    warnings: list[str] = []
    for spec in registry.list_all():
        output = spec.func(series)
        if output is None:
            warnings.append(f"Indicator '{spec.name}' unavailable (insufficient history)")
            continue
        values[spec.name] = output
    return values, warnings
