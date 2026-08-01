"""Mean Reversion requirements checklist (docs/17 §11, merging "Range
Trading"/"Mean Reversion" per ADR-072). Range market, strong support,
strong resistance, low trend strength - all already-computed evidence."""

from app.services.strategy.types import RequirementsResult, StrategyEvidenceBundle
from app.services.technical_analysis.types import TrendStrengthLevel

_STRONG_LEVEL = frozenset({"moderate", "strong"})
_LOW_TREND_STRENGTH = frozenset({TrendStrengthLevel.WEAK, TrendStrengthLevel.MODERATE})


def check(evidence: StrategyEvidenceBundle) -> RequirementsResult:
    if evidence.market_regime is None or evidence.technical is None:
        return RequirementsResult(met_count=0, total_count=4)

    range_market = evidence.market_regime.range.is_ranging

    support = evidence.technical.support
    strong_support = support is not None and support.strength in _STRONG_LEVEL

    resistance = evidence.technical.resistance
    strong_resistance = resistance is not None and resistance.strength in _STRONG_LEVEL

    low_trend_strength = evidence.technical.trend_evidence.strength in _LOW_TREND_STRENGTH

    met_count = sum([range_market, strong_support, strong_resistance, low_trend_strength])
    return RequirementsResult(met_count=met_count, total_count=4)
