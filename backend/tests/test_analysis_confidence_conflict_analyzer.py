from app.services.analysis_confidence import alignment_analyzer, conflict_analyzer
from app.services.analysis_confidence.types import ConflictSeverity, NormalizedDirection
from app.services.smc.types import MarketStructureState
from app.services.technical_analysis.types import TrendDirection
from tests.analysis_confidence_helpers import (
    make_regime_result,
    make_smc_result,
    make_technical_result,
)

_NO_CONFLICT_ALIGNMENT = alignment_analyzer.analyze(
    NormalizedDirection.BULLISH, NormalizedDirection.BULLISH, NormalizedDirection.BULLISH
)


def test_no_conflicts_when_everything_agrees() -> None:
    technical = make_technical_result(trend=TrendDirection.BULLISH, technical_score=70.0)
    smc = make_smc_result(structure_state=MarketStructureState.BULLISH, smc_score=65.0)
    regime = make_regime_result(direction=TrendDirection.BULLISH, aligned=True)

    conflicts = conflict_analyzer.analyze(technical, smc, regime, _NO_CONFLICT_ALIGNMENT)

    assert conflicts == []
    assert conflict_analyzer.penalty_for(conflicts) == 0.0
    assert conflict_analyzer.overall_severity(conflicts) == ConflictSeverity.NONE


def test_technical_vs_smc_direction_conflict_is_high_severity() -> None:
    technical = make_technical_result(trend=TrendDirection.BULLISH)
    smc = make_smc_result(structure_state=MarketStructureState.BEARISH)
    alignment = alignment_analyzer.analyze(
        NormalizedDirection.BULLISH, NormalizedDirection.BEARISH, None
    )

    conflicts = conflict_analyzer.analyze(technical, smc, None, alignment)

    assert any(c.severity == ConflictSeverity.HIGH for c in conflicts)
    assert conflict_analyzer.overall_severity(conflicts) == ConflictSeverity.HIGH


def test_regime_internal_misalignment_is_medium_severity() -> None:
    regime = make_regime_result(aligned=False)

    conflicts = conflict_analyzer.analyze(
        None, None, regime, alignment_analyzer.analyze(None, None, None)
    )

    assert any(c.severity == ConflictSeverity.MEDIUM for c in conflicts)


def test_score_quartile_mismatch_is_detected() -> None:
    technical = make_technical_result(technical_score=90.0)
    smc = make_smc_result(smc_score=10.0)

    conflicts = conflict_analyzer.analyze(
        technical, smc, None, alignment_analyzer.analyze(None, None, None)
    )

    assert any("diverge sharply" in c.description for c in conflicts)


def test_regime_against_majority_conflict() -> None:
    regime = make_regime_result(direction=TrendDirection.BEARISH)
    alignment = alignment_analyzer.analyze(
        NormalizedDirection.BULLISH, NormalizedDirection.BULLISH, NormalizedDirection.BEARISH
    )

    conflicts = conflict_analyzer.analyze(None, None, regime, alignment)

    assert any("opposes the" in c.description for c in conflicts)


def test_penalty_is_floored_at_conflict_penalty_weight() -> None:
    technical = make_technical_result(trend=TrendDirection.BULLISH, technical_score=95.0)
    smc = make_smc_result(structure_state=MarketStructureState.BEARISH, smc_score=5.0)
    regime = make_regime_result(direction=TrendDirection.BEARISH, aligned=False)
    alignment = alignment_analyzer.analyze(
        NormalizedDirection.BULLISH, NormalizedDirection.BEARISH, NormalizedDirection.BEARISH
    )

    conflicts = conflict_analyzer.analyze(technical, smc, regime, alignment)
    penalty = conflict_analyzer.penalty_for(conflicts)

    assert penalty >= conflict_analyzer.CONFLICT_PENALTY_WEIGHT
    assert penalty <= 0.0


def test_missing_engines_produce_no_conflicts() -> None:
    conflicts = conflict_analyzer.analyze(
        None, None, None, alignment_analyzer.analyze(None, None, None)
    )

    assert conflicts == []
