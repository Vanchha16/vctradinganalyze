"""ADR-176 - fixed-distance ("tight") setups, at two timeframes.

Covers the whole feature in one place because it is one decision spread
across four modules: the builder that produces the distances, the
settings resolver that selects them, the orchestrator branch that skips
the LLM for M5, and the engine rule that stops M5 drafting.

The thing most worth protecting here is that **both profiles default
off**. Turning either on changes what the EA actually trades, so a
deploy of this code must not change behaviour on its own.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.config import settings
from app.models.enums import Timeframe
from app.services.ai_orchestrator.candidate_setup_builder import (
    FixedDistances,
    build,
    fixed_distances_for,
)
from app.services.risk_management.types import TradeDirection
from app.services.technical_analysis.types import TrendDirection
from tests.ai_orchestrator_helpers import make_confidence_result, make_strategy_evaluation
from tests.analysis_confidence_helpers import make_regime_result, make_technical_result

_CLOSE = Decimal("100")
_TIGHT = FixedDistances(stop=Decimal("10"), target=Decimal("20"))


@pytest.fixture
def tight_h1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tight_h1_enabled", True)


@pytest.fixture
def tight_m5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tight_m5_enabled", True)


def _bearish_confidence():
    return replace(
        make_confidence_result(),
        technical=make_technical_result(trend=TrendDirection.BEARISH),
        market_regime=make_regime_result(direction=TrendDirection.BEARISH),
    )


# --- The switch --------------------------------------------------------


def test_both_profiles_are_off_by_default() -> None:
    """Deploying this code must not change what the EA trades. The
    operator turns each on deliberately."""
    assert settings.tight_h1_enabled is False
    assert settings.tight_m5_enabled is False
    assert fixed_distances_for(Timeframe.H1) is None
    assert fixed_distances_for(Timeframe.M5) is None


def test_h1_profile_resolves_only_for_h1(tight_h1: None) -> None:
    assert fixed_distances_for(Timeframe.H1) == FixedDistances(
        stop=settings.tight_h1_stop_distance, target=settings.tight_h1_target_distance
    )
    # Switching H1 on must not quietly tighten every other timeframe.
    assert fixed_distances_for(Timeframe.M5) is None
    assert fixed_distances_for(Timeframe.M15) is None
    assert fixed_distances_for(Timeframe.H4) is None


def test_m5_profile_resolves_only_for_m5(tight_m5: None) -> None:
    assert fixed_distances_for(Timeframe.M5) == FixedDistances(
        stop=settings.tight_m5_stop_distance, target=settings.tight_m5_target_distance
    )
    assert fixed_distances_for(Timeframe.H1) is None


def test_default_distances_match_the_adr() -> None:
    """Sized against measured ATR(14): H1 20.14, M5 5.45. Both 1:2, so both
    satisfy `_MIN_RISK_REWARD_MULTIPLE`."""
    assert (settings.tight_h1_stop_distance, settings.tight_h1_target_distance) == (
        Decimal("10"),
        Decimal("20"),
    )
    assert (settings.tight_m5_stop_distance, settings.tight_m5_target_distance) == (
        Decimal("5"),
        Decimal("10"),
    )


# --- The builder -------------------------------------------------------


def test_fixed_distances_set_a_long_stop_and_target_exactly() -> None:
    setup = build(make_confidence_result(), make_strategy_evaluation(), _CLOSE, _TIGHT)

    assert setup is not None
    assert setup.direction is TradeDirection.LONG
    assert setup.entry_price == _CLOSE
    assert setup.stop_loss == Decimal("90")
    assert setup.take_profit == Decimal("120")


def test_fixed_distances_set_a_short_stop_and_target_exactly() -> None:
    """A short's stop is above entry and its target below - the mirror of
    the long, not the same arithmetic."""
    setup = build(_bearish_confidence(), make_strategy_evaluation(), _CLOSE, _TIGHT)

    assert setup is not None
    assert setup.direction is TradeDirection.SHORT
    assert setup.stop_loss == Decimal("110")
    assert setup.take_profit == Decimal("80")


def test_fixed_distances_ignore_atr_and_structure_entirely() -> None:
    """The whole point: the ATR path takes the *more conservative* of
    1.5xATR or structure, which is why it cannot go tight. A fixed profile
    must not be widened by either."""
    wide = build(make_confidence_result(), make_strategy_evaluation(), _CLOSE)
    tight = build(make_confidence_result(), make_strategy_evaluation(), _CLOSE, _TIGHT)

    assert wide is not None and tight is not None
    assert abs(tight.entry_price - tight.stop_loss) == Decimal("10")
    assert abs(wide.entry_price - wide.stop_loss) != abs(tight.entry_price - tight.stop_loss)


def test_a_tight_setup_still_refuses_an_ambiguous_regime() -> None:
    """Fixed distances change the distances, not whether a setup exists. A
    tight signal must be as unwilling to invent a trade as a wide one."""
    regime = make_regime_result()
    confidence = replace(
        make_confidence_result(),
        market_regime=replace(
            regime, trend_regime=replace(regime.trend_regime, direction=TrendDirection.SIDEWAYS)
        ),
    )

    assert build(confidence, make_strategy_evaluation(), _CLOSE, _TIGHT) is None


def test_a_tight_setup_still_refuses_without_a_real_price() -> None:
    """ADR-145: no price, no candidate. A fixed distance from a fabricated
    entry is still a fabricated trade."""
    assert build(make_confidence_result(), make_strategy_evaluation(), None, _TIGHT) is None


def test_a_tight_setup_still_refuses_without_a_primary_strategy() -> None:
    assert (
        build(
            make_confidence_result(),
            make_strategy_evaluation(primary_strategy=None),
            _CLOSE,
            _TIGHT,
        )
        is None
    )


# --- Scheduling --------------------------------------------------------


def test_the_m5_schedule_is_registered_every_five_minutes() -> None:
    from app.workers.signal_tasks import register_signal_schedule

    schedule = register_signal_schedule()

    assert "generate-signals-tight-m5" in schedule
    entry = schedule["generate-signals-tight-m5"]
    assert entry["task"] == "signals.generate_tight_m5"
    assert str(entry["schedule"].minute) == str({0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55})


def test_the_m5_task_does_nothing_while_the_strategy_is_off() -> None:
    """Beat enqueues unconditionally so the switch needs no Beat restart -
    which only works if a disabled run is genuinely free. If this ever
    opens a session or builds an engine, the 12x cadence starts costing
    something while switched off."""
    import app.workers.signal_tasks as signal_tasks

    called = False

    def _fail(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    original = signal_tasks._generate_for_timeframe
    signal_tasks._generate_for_timeframe = _fail  # type: ignore[assignment]
    try:
        signal_tasks.generate_tight_m5_signals_task()
    finally:
        signal_tasks._generate_for_timeframe = original  # type: ignore[assignment]

    assert called is False


def test_the_m5_task_runs_on_m5_when_switched_on(tight_m5: None) -> None:
    import app.workers.signal_tasks as signal_tasks

    seen: list[Timeframe] = []
    original = signal_tasks._generate_for_timeframe
    signal_tasks._generate_for_timeframe = seen.append  # type: ignore[assignment]
    try:
        signal_tasks.generate_tight_m5_signals_task()
    finally:
        signal_tasks._generate_for_timeframe = original  # type: ignore[assignment]

    assert seen == [Timeframe.M5]
