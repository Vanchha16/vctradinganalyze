"""Deterministic per-strategy score aggregation (docs/17 §14, docs/49
§7). Mirrors `risk_management.trade_quality_aggregator`'s pattern - not
a shared aggregator, since the weights/semantics differ per engine."""

from app.models.enums import Timeframe
from app.services.market_regime.types import VolatilityRegimeState
from app.services.risk_management.types import LiquidityClassification, MarketSession
from app.services.strategy import historical_performance, market_match
from app.services.strategy.requirements import (
    breakout,
    mean_reversion,
    pullback,
    scalping,
    smc,
    swing_trading,
    trend_following,
)
from app.services.strategy.types import (
    RequirementsResult,
    StrategyBreakdown,
    StrategyEvidenceBundle,
    StrategyName,
)

_EVIDENCE_QUALITY_WEIGHT = 25.0
_CONFIDENCE_WEIGHT = 20.0
_RISK_WEIGHT = 15.0

_REQUIREMENTS_CHECKERS = {
    StrategyName.TREND_FOLLOWING: trend_following.check,
    StrategyName.SMC: smc.check,
    StrategyName.BREAKOUT: breakout.check,
    StrategyName.PULLBACK: pullback.check,
    StrategyName.MEAN_REVERSION: mean_reversion.check,
    StrategyName.SCALPING: scalping.check,
    StrategyName.SWING_TRADING: swing_trading.check,
}

_LOW_LIQUIDITY_PENALTY = -3.0
_CLOSED_SESSION_PENALTY = -3.0
_CRITICAL_EVENT_PENALTY = -5.0
_EXTREME_VOLATILITY_PENALTY = -3.0


def _requirements_for(
    strategy: StrategyName, evidence: StrategyEvidenceBundle
) -> RequirementsResult:
    return _REQUIREMENTS_CHECKERS[strategy](evidence)


def _risk_component(evidence: StrategyEvidenceBundle) -> float:
    risk = _RISK_WEIGHT
    if evidence.session is MarketSession.CLOSED:
        risk += _CLOSED_SESSION_PENALTY
    if evidence.liquidity is LiquidityClassification.LOW:
        risk += _LOW_LIQUIDITY_PENALTY
    if evidence.economic.hard_reject:
        risk += _CRITICAL_EVENT_PENALTY
    if (
        evidence.market_regime is not None
        and evidence.market_regime.volatility.state is VolatilityRegimeState.EXTREME
    ):
        risk += _EXTREME_VOLATILITY_PENALTY
    return max(0.0, risk)


def score(
    strategy: StrategyName, evidence: StrategyEvidenceBundle, timeframe: Timeframe
) -> StrategyBreakdown:
    regime = evidence.market_regime.regime if evidence.market_regime is not None else None
    market_match_score = market_match.score(strategy, regime, timeframe)

    requirements = _requirements_for(strategy, evidence)
    evidence_quality_score = _EVIDENCE_QUALITY_WEIGHT * requirements.ratio

    confidence_score = evidence.overall_confidence / 100 * _CONFIDENCE_WEIGHT

    risk_score = _risk_component(evidence)

    historical_score = historical_performance.score()

    return StrategyBreakdown(
        market_match=market_match_score,
        evidence_quality=evidence_quality_score,
        confidence=confidence_score,
        risk=risk_score,
        historical_performance=historical_score,
    )
