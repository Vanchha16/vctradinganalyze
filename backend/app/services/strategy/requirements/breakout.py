"""Breakout requirements checklist (docs/17 §9, docs/49 §5). Resistance/
support break, volume confirmation, momentum increase, healthy
volatility - all already-computed evidence."""

from app.services.market_regime.types import VolatilityRegimeState
from app.services.strategy.types import RequirementsResult, StrategyEvidenceBundle

_HEALTHY_VOLATILITY = frozenset({VolatilityRegimeState.NORMAL, VolatilityRegimeState.HIGH})


def check(evidence: StrategyEvidenceBundle) -> RequirementsResult:
    if evidence.market_regime is None or evidence.technical is None:
        return RequirementsResult(met_count=0, total_count=4)

    breakout = evidence.market_regime.breakout
    resistance_break = breakout.detected
    volume_confirmed = breakout.volume_confirmed

    momentum = evidence.technical.momentum
    momentum_increase = bool(momentum.macd_bullish) or bool(momentum.momentum_positive)

    healthy_volatility = evidence.market_regime.volatility.state in _HEALTHY_VOLATILITY

    met_count = sum([resistance_break, volume_confirmed, momentum_increase, healthy_volatility])
    return RequirementsResult(met_count=met_count, total_count=4)
