from app.models.enums import Timeframe
from app.services.market_regime.types import MarketRegimeState
from app.services.strategy.market_match import score
from app.services.strategy.types import StrategyName


def test_full_match_regime_and_timeframe_compatible() -> None:
    result = score(StrategyName.TREND_FOLLOWING, MarketRegimeState.TRENDING_BULLISH, Timeframe.H1)
    assert result == 30.0


def test_partial_match_regime_compatible_timeframe_not_preferred() -> None:
    result = score(StrategyName.TREND_FOLLOWING, MarketRegimeState.TRENDING_BULLISH, Timeframe.M15)
    assert result == 20.0


def test_no_match_regime_incompatible() -> None:
    result = score(StrategyName.TREND_FOLLOWING, MarketRegimeState.RANGING, Timeframe.H1)
    assert result == 0.0


def test_no_match_when_regime_is_none() -> None:
    result = score(StrategyName.TREND_FOLLOWING, None, Timeframe.H1)
    assert result == 0.0


def test_mean_reversion_matches_ranging_only() -> None:
    assert score(StrategyName.MEAN_REVERSION, MarketRegimeState.RANGING, Timeframe.H1) == 30.0
    assert (
        score(StrategyName.MEAN_REVERSION, MarketRegimeState.TRENDING_BULLISH, Timeframe.H1) == 0.0
    )


def test_smc_matches_accumulation_and_distribution() -> None:
    assert score(StrategyName.SMC, MarketRegimeState.ACCUMULATION, Timeframe.H1) == 30.0
    assert score(StrategyName.SMC, MarketRegimeState.DISTRIBUTION, Timeframe.H1) == 30.0


def test_breakout_matches_breakout_regime_only() -> None:
    assert score(StrategyName.BREAKOUT, MarketRegimeState.BREAKOUT, Timeframe.H1) == 30.0
    assert score(StrategyName.BREAKOUT, MarketRegimeState.RANGING, Timeframe.H1) == 0.0
