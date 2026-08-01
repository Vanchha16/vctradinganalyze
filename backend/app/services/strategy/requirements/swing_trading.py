"""Swing Trading requirements checklist (docs/17 §13, docs/49 §5).
Higher-timeframe trend (evaluated on the requested timeframe's own
evidence, not a separate higher-timeframe fetch - out of scope, docs/49
§11), strong structure, medium volatility. Healthy RR is excluded (no
candidate setup, ADR-074)."""

from app.services.market_regime.types import VolatilityRegimeState
from app.services.smc.types import MarketStructureState
from app.services.strategy.types import RequirementsResult, StrategyEvidenceBundle
from app.services.technical_analysis.types import TrendStrengthLevel

_STRONG_TREND = frozenset({TrendStrengthLevel.STRONG, TrendStrengthLevel.VERY_STRONG})
_STRONG_STRUCTURE = frozenset({MarketStructureState.BULLISH, MarketStructureState.BEARISH})


def check(evidence: StrategyEvidenceBundle) -> RequirementsResult:
    if evidence.technical is None or evidence.smc is None or evidence.market_regime is None:
        return RequirementsResult(met_count=0, total_count=3)

    higher_timeframe_trend = evidence.technical.trend_evidence.strength in _STRONG_TREND

    strong_structure = evidence.smc.market_structure.state in _STRONG_STRUCTURE

    medium_volatility = evidence.market_regime.volatility.state is VolatilityRegimeState.NORMAL

    met_count = sum([higher_timeframe_trend, strong_structure, medium_volatility])
    return RequirementsResult(met_count=met_count, total_count=3)
