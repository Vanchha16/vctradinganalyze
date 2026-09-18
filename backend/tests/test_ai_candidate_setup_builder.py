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


# --- ADR-179: a BBMA signal is priced by BBMA's own rules -----------------

from app.services.bbma.types import (  # noqa: E402
    BBMAConditions,
    BBMADirection,
    BBMAResult,
    BBMASetup,
    BBMASetupKind,
)
from app.services.strategy.types import StrategyName  # noqa: E402


def _bbma(
    *,
    direction: BBMADirection = BBMADirection.SELL,
    entry: float = 118.0,
    stop: float = 118.4,
    target: float = 112.0,
    entry_index: int = 99,
    bar_count: int = 100,
) -> BBMAResult:
    setup = BBMASetup(
        kind=BBMASetupKind.EXTREME,
        direction=direction,
        entry_index=entry_index,
        marked_level=entry,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target,
    )
    conditions = BBMAConditions(
        csm=False, csak=False, csk=False, zzl=False, trend_major=direction, bb_expanding=True
    )
    return BBMAResult(
        symbol="XAUUSD", timeframe="h1", setups=[setup], conditions=conditions, bar_count=bar_count
    )


def test_a_bbma_signal_uses_the_setups_own_levels() -> None:
    """Entry at the marked level, stop beyond the reverse wick, target TP
    Wajib - taken from the setup, not from the ATR formula."""
    strategy = make_strategy_evaluation(primary_strategy=StrategyName.BBMA, bbma=_bbma())

    setup = build(make_confidence_result(), strategy, _CLOSE)

    assert setup is not None
    assert setup.direction is TradeDirection.SHORT
    assert (setup.entry_price, setup.stop_loss, setup.take_profit) == (
        Decimal("118.0"),
        Decimal("118.4"),
        Decimal("112.0"),
    )


def test_a_bbma_signal_takes_its_direction_from_the_setup_not_the_trend() -> None:
    """The default confidence fixture reads BULLISH; the BBMA setup says
    SELL. BBMA's own rule decides, and its trend-major check lives in its
    requirements checklist."""
    strategy = make_strategy_evaluation(primary_strategy=StrategyName.BBMA, bbma=_bbma())

    setup = build(make_confidence_result(), strategy, _CLOSE)

    assert setup is not None and setup.direction is TradeDirection.SHORT


def test_a_bbma_buy_mirrors_the_sell() -> None:
    bbma = _bbma(direction=BBMADirection.BUY, entry=90.0, stop=89.6, target=96.0)
    strategy = make_strategy_evaluation(primary_strategy=StrategyName.BBMA, bbma=bbma)

    setup = build(make_confidence_result(), strategy, _CLOSE)

    assert setup is not None
    assert setup.direction is TradeDirection.LONG
    assert setup.stop_loss < setup.entry_price < setup.take_profit


def test_a_stale_bbma_setup_trades_nothing() -> None:
    """With the entry at the marked level, an old setup would place an
    order at a price the market left long ago."""
    strategy = make_strategy_evaluation(
        primary_strategy=StrategyName.BBMA, bbma=_bbma(entry_index=50, bar_count=100)
    )

    assert build(make_confidence_result(), strategy, _CLOSE) is None


def test_bbma_without_a_setup_trades_nothing_and_never_falls_back() -> None:
    """A 'BBMA' order priced by the generic ATR formula is exactly what
    ADR-179 removed, so no setup means WAIT, not a generic trade."""
    empty = BBMAResult(symbol="XAUUSD", timeframe="h1", setups=[], conditions=None, bar_count=100)
    for bbma in (None, empty):
        strategy = make_strategy_evaluation(primary_strategy=StrategyName.BBMA, bbma=bbma)
        assert build(make_confidence_result(), strategy, _CLOSE) is None


def test_an_inverted_bbma_setup_never_reaches_the_ea() -> None:
    """A sell whose stop is below its entry would be a wrong-side order."""
    strategy = make_strategy_evaluation(primary_strategy=StrategyName.BBMA, bbma=_bbma(stop=117.0))

    assert build(make_confidence_result(), strategy, _CLOSE) is None


def test_other_strategies_still_use_the_generic_rule() -> None:
    """Only BBMA changed; a BBMA result sitting in the evaluation must not
    re-price a trend-following signal."""
    strategy = make_strategy_evaluation(primary_strategy=StrategyName.TREND_FOLLOWING, bbma=_bbma())

    setup = build(make_confidence_result(), strategy, _CLOSE)

    assert setup is not None and setup.entry_price == _CLOSE
