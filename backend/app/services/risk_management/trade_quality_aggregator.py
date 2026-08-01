"""Deterministic Trade Quality Score aggregation (docs/12 §15, docs/48
§7). Mirrors `confidence_aggregator.combine`'s weighted-component
pattern (ADR-046) but scoped to this engine's own components - not a
shared aggregator, since the weights/semantics differ."""

from app.services.risk_management.types import TradeQualityBreakdown

_TREND_QUALITY_WEIGHT = 20.0
_TECHNICAL_WEIGHT = 20.0
_SMC_WEIGHT = 20.0
_RISK_WEIGHT = 20.0

_TREND_QUALITY_SCORES: dict[str, float] = {
    "weak": 5.0,
    "moderate": 12.0,
    "strong": 17.0,
    "very_strong": 20.0,
}


def trend_quality_score(trend_strength: str | None) -> float:
    if trend_strength is None:
        return 0.0
    return _TREND_QUALITY_SCORES.get(trend_strength, 0.0)


def aggregate(
    *,
    trend_strength: str | None,
    technical_score: float | None,
    smc_score: float | None,
    risk_penalties: list[float],
    news_score: float,
    economic_score: float,
) -> TradeQualityBreakdown:
    trend_quality = trend_quality_score(trend_strength)
    technical = (technical_score / 100 * _TECHNICAL_WEIGHT) if technical_score is not None else 0.0
    smc = (smc_score / 100 * _SMC_WEIGHT) if smc_score is not None else 0.0
    risk = max(0.0, _RISK_WEIGHT + sum(risk_penalties))

    return TradeQualityBreakdown(
        trend_quality=trend_quality,
        technical=technical,
        smc=smc,
        risk=risk,
        news=news_score,
        economic=economic_score,
    )
