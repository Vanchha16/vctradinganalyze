from app.services.market_regime import expansion_analyzer
from app.services.market_regime.types import (
    ExpansionState,
    VolatilityRegimeEvidence,
    VolatilityRegimeState,
)


def test_expansion_when_recent_average_much_higher() -> None:
    volatility = VolatilityRegimeEvidence(
        state=VolatilityRegimeState.HIGH, recent_atr_average=2.0, baseline_atr_average=1.0
    )

    evidence = expansion_analyzer.analyze(volatility)

    assert evidence.state == ExpansionState.EXPANSION
    assert evidence.ratio == 2.0


def test_contraction_when_recent_average_much_lower() -> None:
    volatility = VolatilityRegimeEvidence(
        state=VolatilityRegimeState.LOW, recent_atr_average=0.5, baseline_atr_average=1.0
    )

    evidence = expansion_analyzer.analyze(volatility)

    assert evidence.state == ExpansionState.CONTRACTION


def test_stable_when_averages_close() -> None:
    volatility = VolatilityRegimeEvidence(
        state=VolatilityRegimeState.NORMAL, recent_atr_average=1.0, baseline_atr_average=1.0
    )

    evidence = expansion_analyzer.analyze(volatility)

    assert evidence.state == ExpansionState.STABLE


def test_missing_averages_returns_stable_with_no_ratio() -> None:
    volatility = VolatilityRegimeEvidence(
        state=VolatilityRegimeState.NORMAL, recent_atr_average=None, baseline_atr_average=None
    )

    evidence = expansion_analyzer.analyze(volatility)

    assert evidence.state == ExpansionState.STABLE
    assert evidence.ratio is None
