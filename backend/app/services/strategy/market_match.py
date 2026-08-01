"""Deterministic Market Match scoring (docs/17 §14, docs/49 §6,
ADR-073). A regime-compatibility gate with timeframe partial credit -
a regime-incompatible strategy scores 0 here but is not automatically
excluded from the overall breakdown (rejection is a separate downstream
decision, ADR-076)."""

from app.models.enums import Timeframe
from app.services.market_regime.types import MarketRegimeState
from app.services.strategy.types import StrategyName

_FULL_MATCH_SCORE = 30.0
_PARTIAL_MATCH_SCORE = 20.0
_NO_MATCH_SCORE = 0.0

# docs/49 §4's table.
_COMPATIBLE_REGIMES: dict[StrategyName, frozenset[MarketRegimeState]] = {
    StrategyName.TREND_FOLLOWING: frozenset(
        {MarketRegimeState.TRENDING_BULLISH, MarketRegimeState.TRENDING_BEARISH}
    ),
    StrategyName.SMC: frozenset(
        {
            MarketRegimeState.TRENDING_BULLISH,
            MarketRegimeState.TRENDING_BEARISH,
            MarketRegimeState.ACCUMULATION,
            MarketRegimeState.DISTRIBUTION,
        }
    ),
    StrategyName.BREAKOUT: frozenset({MarketRegimeState.BREAKOUT}),
    StrategyName.PULLBACK: frozenset(
        {
            MarketRegimeState.PULLBACK,
            MarketRegimeState.TRENDING_BULLISH,
            MarketRegimeState.TRENDING_BEARISH,
        }
    ),
    StrategyName.MEAN_REVERSION: frozenset({MarketRegimeState.RANGING}),
    StrategyName.SCALPING: frozenset(
        {
            MarketRegimeState.TRENDING_BULLISH,
            MarketRegimeState.TRENDING_BEARISH,
            MarketRegimeState.RANGING,
            MarketRegimeState.BREAKOUT,
        }
    ),
    StrategyName.SWING_TRADING: frozenset(
        {
            MarketRegimeState.TRENDING_BULLISH,
            MarketRegimeState.TRENDING_BEARISH,
            MarketRegimeState.ACCUMULATION,
            MarketRegimeState.DISTRIBUTION,
        }
    ),
}

_PREFERRED_TIMEFRAMES: dict[StrategyName, frozenset[Timeframe]] = {
    StrategyName.TREND_FOLLOWING: frozenset({Timeframe.H1, Timeframe.H4, Timeframe.D1}),
    StrategyName.SMC: frozenset({Timeframe.M15, Timeframe.H1, Timeframe.H4}),
    StrategyName.BREAKOUT: frozenset({Timeframe.H1, Timeframe.H4, Timeframe.D1}),
    StrategyName.PULLBACK: frozenset({Timeframe.H1, Timeframe.H4}),
    StrategyName.MEAN_REVERSION: frozenset({Timeframe.H1, Timeframe.H4}),
    StrategyName.SCALPING: frozenset({Timeframe.M1, Timeframe.M5}),
    StrategyName.SWING_TRADING: frozenset({Timeframe.H4, Timeframe.D1, Timeframe.W1}),
}


def compatible_regimes_for(strategy: StrategyName) -> frozenset[MarketRegimeState]:
    return _COMPATIBLE_REGIMES[strategy]


def preferred_timeframes_for(strategy: StrategyName) -> frozenset[Timeframe]:
    return _PREFERRED_TIMEFRAMES[strategy]


def score(strategy: StrategyName, regime: MarketRegimeState | None, timeframe: Timeframe) -> float:
    if regime is None or regime not in _COMPATIBLE_REGIMES[strategy]:
        return _NO_MATCH_SCORE
    if timeframe in _PREFERRED_TIMEFRAMES[strategy]:
        return _FULL_MATCH_SCORE
    return _PARTIAL_MATCH_SCORE
