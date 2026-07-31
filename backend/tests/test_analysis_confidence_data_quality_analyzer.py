from app.services.analysis_confidence import data_quality_analyzer
from app.services.market_regime.types import MarketRegimeState
from tests.analysis_confidence_helpers import (
    make_regime_result,
    make_smc_result,
    make_technical_result,
)


def test_complete_evidence_has_full_completeness_score() -> None:
    technical = make_technical_result(has_support_resistance=True)
    smc = make_smc_result(has_structural_evidence=True)
    regime = make_regime_result(regime=MarketRegimeState.TRENDING_BULLISH)

    result = data_quality_analyzer.analyze(technical, smc, regime)

    assert result.missing_data == []
    assert result.completeness_score == data_quality_analyzer.DATA_COMPLETENESS_WEIGHT


def test_missing_support_resistance_is_flagged() -> None:
    technical = make_technical_result(has_support_resistance=False)
    smc = make_smc_result()
    regime = make_regime_result()

    result = data_quality_analyzer.analyze(technical, smc, regime)

    assert "no_support_resistance_levels" in result.missing_data


def test_missing_smc_structural_evidence_is_flagged() -> None:
    technical = make_technical_result()
    smc = make_smc_result(has_structural_evidence=False)
    regime = make_regime_result()

    result = data_quality_analyzer.analyze(technical, smc, regime)

    assert "smc_no_structural_evidence" in result.missing_data


def test_uncertain_regime_is_flagged() -> None:
    technical = make_technical_result()
    smc = make_smc_result()
    regime = make_regime_result(regime=MarketRegimeState.UNCERTAIN)

    result = data_quality_analyzer.analyze(technical, smc, regime)

    assert "market_regime_uncertain" in result.missing_data


def test_all_engines_unavailable_reduces_completeness_score() -> None:
    result = data_quality_analyzer.analyze(None, None, None)

    assert "technical_analysis_unavailable" in result.missing_data
    assert "smc_unavailable" in result.missing_data
    assert "market_regime_unavailable" in result.missing_data
    assert result.completeness_score < data_quality_analyzer.DATA_COMPLETENESS_WEIGHT


def test_completeness_score_never_goes_negative() -> None:
    # More missing signals than the module tracks would still floor at 0 -
    # exercised here via the real (currently 6-signal) worst case.
    result = data_quality_analyzer.analyze(None, None, None)

    assert result.completeness_score >= 0.0
