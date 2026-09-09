from dataclasses import replace
from decimal import Decimal

from app.services.ai_orchestrator.candidate_setup_builder import build
from app.services.risk_management.types import TradeDirection
from app.services.technical_analysis.types import TrendDirection
from tests.ai_orchestrator_helpers import make_confidence_result, make_strategy_evaluation
from tests.analysis_confidence_helpers import make_regime_result, make_technical_result

#: ADR-145: entry is now the caller-supplied real traded price, not a
#: support/resistance midpoint derived inside the builder.
_CLOSE = Decimal("100")


def test_build_returns_none_when_no_primary_strategy() -> None:
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation(primary_strategy=None)
    assert build(confidence, strategy, _CLOSE) is None


def test_build_returns_none_when_no_technical_evidence() -> None:
    confidence = make_confidence_result(include_technical=False)
    strategy = make_strategy_evaluation()
    assert build(confidence, strategy, _CLOSE) is None


def test_build_returns_none_when_regime_direction_is_sideways() -> None:
    regime = make_regime_result()
    regime = replace(
        regime, trend_regime=replace(regime.trend_regime, direction=TrendDirection.SIDEWAYS)
    )
    confidence = make_confidence_result()
    confidence = replace(confidence, market_regime=regime)
    strategy = make_strategy_evaluation()

    assert build(confidence, strategy, _CLOSE) is None


def test_build_returns_long_setup_for_bullish_regime() -> None:
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation()

    setup = build(confidence, strategy, _CLOSE)

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

    setup = build(confidence, strategy, _CLOSE)

    assert setup is not None
    assert setup.direction is TradeDirection.SHORT
    assert setup.stop_loss > setup.entry_price
    assert setup.take_profit < setup.entry_price


def test_build_risk_reward_is_at_least_2_to_1() -> None:
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation()

    setup = build(confidence, strategy, _CLOSE)

    assert setup is not None
    risk = abs(setup.entry_price - setup.stop_loss)
    reward = abs(setup.take_profit - setup.entry_price)
    assert reward >= risk * 2


# --- ADR-145: entry is the real traded price ---------------------------
#
# The bug these encode: `build` used to derive entry as the midpoint of
# support and resistance, in a helper named `_latest_close`. Because a
# candidate is only built when the regime is trending - and in a trend
# price sits near a range extreme, not its middle - the entry landed on
# the unfillable side of the market. Production, 14 days: 10 of 14
# entries were away from market and the 4 that never filled had the
# largest gaps.


def test_entry_is_exactly_the_supplied_close_not_a_derived_level() -> None:
    """The core of ADR-145. `make_technical_result`'s support/resistance
    midpoint is deliberately nowhere near this close, so a builder that
    still derived entry internally would fail here."""
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation()

    setup = build(confidence, strategy, Decimal("4369.30"))

    assert setup is not None
    assert setup.entry_price == Decimal("4369.30")


def test_entry_tracks_the_close_rather_than_the_support_resistance_midpoint() -> None:
    """Two different market prices against identical technical evidence
    must produce two different entries. Under the old midpoint logic both
    calls returned the *same* entry regardless of where price actually
    was - which is precisely how a SELL got an entry 15 points above
    market."""
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation()

    low = build(confidence, strategy, Decimal("4300"))
    high = build(confidence, strategy, Decimal("4400"))

    assert low is not None and high is not None
    assert low.entry_price != high.entry_price
    assert low.entry_price == Decimal("4300")
    assert high.entry_price == Decimal("4400")


def test_risk_distance_and_target_move_with_the_entry() -> None:
    """Entry anchors every other level, so fixing entry also fixes the
    real (as opposed to nominal) risk/reward of every signal.

    The *stop* deliberately does not move here: it is pinned to
    structural support, which `_more_conservative_long_stop` prefers
    whenever it sits further away than the ATR stop. What moves is the
    distance from entry to that stop - and therefore the target, since
    the target is `entry ± 2 × risk`.

    Closes are chosen inside the fixture's own 1.1000-1.1100 range, so
    both stops resolve the same way and the comparison isolates entry."""
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation()

    near = build(confidence, strategy, Decimal("1.1020"))
    far = build(confidence, strategy, Decimal("1.1080"))

    assert near is not None and far is not None
    near_risk = abs(near.entry_price - near.stop_loss)
    far_risk = abs(far.entry_price - far.stop_loss)
    assert far_risk > near_risk  # entry further from support = more risk
    assert near.take_profit != far.take_profit

    for setup in (near, far):
        risk = abs(setup.entry_price - setup.stop_loss)
        reward = abs(setup.take_profit - setup.entry_price)
        assert risk > 0
        assert reward >= risk * 2


def test_build_returns_none_without_a_price_rather_than_guessing_one() -> None:
    """No silent fallback to the old midpoint: no price means no
    candidate, which yields WAIT (ADR-011). A known-wrong entry is worse
    than no recommendation."""
    confidence = make_confidence_result()
    strategy = make_strategy_evaluation()

    assert build(confidence, strategy, None) is None
