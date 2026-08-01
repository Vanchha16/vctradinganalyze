from dataclasses import replace

from app.services.ai_orchestrator.candidate_setup_builder import build
from app.services.risk_management.types import TradeDirection
from app.services.technical_analysis.types import TrendDirection
from tests.ai_orchestrator_helpers import make_confidence_result, make_strategy_evaluation
from tests.analysis_confidence_helpers import make_regime_result, make_technical_result


def test_build_returns_none_when_no_primary_strategy() -> None:
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation(primary_strategy=None)
    assert build(confidence, strategy) is None


def test_build_returns_none_when_no_technical_evidence() -> None:
    confidence = make_confidence_result(include_technical=False)
    strategy = make_strategy_evaluation()
    assert build(confidence, strategy) is None


def test_build_returns_none_when_regime_direction_is_sideways() -> None:
    regime = make_regime_result()
    regime = replace(
        regime, trend_regime=replace(regime.trend_regime, direction=TrendDirection.SIDEWAYS)
    )
    confidence = make_confidence_result()
    confidence = replace(confidence, market_regime=regime)
    strategy = make_strategy_evaluation()

    assert build(confidence, strategy) is None


def test_build_returns_long_setup_for_bullish_regime() -> None:
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation()

    setup = build(confidence, strategy)

    assert setup is not None
    assert setup.direction is TradeDirection.LONG
    assert setup.stop_loss < setup.entry_price
    assert setup.take_profit > setup.entry_price


def test_build_returns_short_setup_for_bearish_regime() -> None:
    technical = make_technical_result(trend=TrendDirection.BEARISH)
    regime = make_regime_result(direction=TrendDirection.BEARISH)
    confidence = make_confidence_result()
    confidence = replace(confidence, technical=technical, market_regime=regime)
    strategy = make_strategy_evaluation()

    setup = build(confidence, strategy)

    assert setup is not None
    assert setup.direction is TradeDirection.SHORT
    assert setup.stop_loss > setup.entry_price
    assert setup.take_profit < setup.entry_price


def test_build_risk_reward_is_at_least_2_to_1() -> None:
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation()

    setup = build(confidence, strategy)

    assert setup is not None
    risk = abs(setup.entry_price - setup.stop_loss)
    reward = abs(setup.take_profit - setup.entry_price)
    assert reward >= risk * 2
