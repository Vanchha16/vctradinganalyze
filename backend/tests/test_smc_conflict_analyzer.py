from app.services.smc import conflict_analyzer
from app.services.smc.types import MarketStructureState


def test_aligned_states_have_no_conflict() -> None:
    report = conflict_analyzer.analyze(MarketStructureState.BULLISH, MarketStructureState.BULLISH)

    assert report.is_pullback is False
    assert report.conflicts == []


def test_opposing_states_classified_as_pullback() -> None:
    report = conflict_analyzer.analyze(MarketStructureState.BULLISH, MarketStructureState.BEARISH)

    assert report.is_pullback is True
    assert report.conflicts == ["higher_bullish_lower_bearish"]


def test_range_state_is_not_a_hard_conflict() -> None:
    report = conflict_analyzer.analyze(MarketStructureState.BULLISH, MarketStructureState.RANGE)

    assert report.is_pullback is False
    assert report.conflicts == []
