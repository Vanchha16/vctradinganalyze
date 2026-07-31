from app.services.market_regime import conflict_analyzer
from app.services.market_regime.types import (
    AccumulationDistributionEvidence,
    RangeEvidence,
    TrendRegimeEvidence,
)
from app.services.smc.types import MarketStructureState
from app.services.technical_analysis.types import TrendDirection, TrendStrengthLevel

_NO_STRUCTURE_CONFLICT = AccumulationDistributionEvidence(
    accumulation_score=0.0, distribution_score=0.0
)
_NOT_RANGING = RangeEvidence(is_ranging=False, range_width=None, range_strength=None)


def _trend_regime(strength: TrendStrengthLevel, aligned: bool) -> TrendRegimeEvidence:
    return TrendRegimeEvidence(
        direction=TrendDirection.BULLISH,
        strength=strength,
        structure_state=MarketStructureState.BULLISH if aligned else MarketStructureState.BEARISH,
        aligned=aligned,
    )


def test_no_conflicts_when_everything_agrees() -> None:
    trend_regime = _trend_regime(TrendStrengthLevel.STRONG, aligned=True)

    report = conflict_analyzer.analyze(trend_regime, _NOT_RANGING, _NO_STRUCTURE_CONFLICT)

    assert report.conflicts == []


def test_conflict_when_strong_trend_and_ranging() -> None:
    trend_regime = _trend_regime(TrendStrengthLevel.STRONG, aligned=True)
    ranging = RangeEvidence(is_ranging=True, range_width=None, range_strength="weak")

    report = conflict_analyzer.analyze(trend_regime, ranging, _NO_STRUCTURE_CONFLICT)

    assert len(report.conflicts) == 1


def test_conflict_when_ta_and_smc_disagree() -> None:
    trend_regime = _trend_regime(TrendStrengthLevel.WEAK, aligned=False)

    report = conflict_analyzer.analyze(trend_regime, _NOT_RANGING, _NO_STRUCTURE_CONFLICT)

    assert len(report.conflicts) == 1


def test_conflict_when_both_accumulation_and_distribution_high() -> None:
    trend_regime = _trend_regime(TrendStrengthLevel.WEAK, aligned=True)
    both_high = AccumulationDistributionEvidence(accumulation_score=70.0, distribution_score=70.0)

    report = conflict_analyzer.analyze(trend_regime, _NOT_RANGING, both_high)

    assert len(report.conflicts) == 1
