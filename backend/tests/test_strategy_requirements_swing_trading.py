from dataclasses import replace

from app.services.market_regime.types import (
    MarketRegimeResult,
    VolatilityRegimeEvidence,
    VolatilityRegimeState,
)
from app.services.smc.types import MarketStructureEvidence, MarketStructureState, SMCAnalysisResult
from app.services.strategy.requirements.swing_trading import check
from app.services.technical_analysis.types import TechnicalAnalysisResult, TrendStrengthLevel
from tests.analysis_confidence_helpers import (
    make_regime_result,
    make_smc_result,
    make_technical_result,
)
from tests.strategy_helpers import make_evidence_bundle


def _strong_trend_technical() -> TechnicalAnalysisResult:
    technical = make_technical_result()
    return replace(
        technical,
        trend_evidence=replace(technical.trend_evidence, strength=TrendStrengthLevel.STRONG),
    )


def _structured_smc() -> SMCAnalysisResult:
    smc = make_smc_result()
    return replace(
        smc,
        market_structure=MarketStructureEvidence(
            state=MarketStructureState.BULLISH, classifications=[]
        ),
    )


def _normal_volatility_regime() -> MarketRegimeResult:
    regime = make_regime_result()
    return replace(
        regime,
        volatility=VolatilityRegimeEvidence(
            state=VolatilityRegimeState.NORMAL, recent_atr_average=1.0, baseline_atr_average=1.0
        ),
    )


def test_check_full_swing_trading_setup() -> None:
    evidence = make_evidence_bundle(
        technical=_strong_trend_technical(),
        smc=_structured_smc(),
        market_regime=_normal_volatility_regime(),
    )
    result = check(evidence)
    assert result.met_count == 3
    assert result.total_count == 3


def test_check_range_structure_reduces_matches() -> None:
    smc = make_smc_result(structure_state=MarketStructureState.RANGE)
    evidence = make_evidence_bundle(smc=smc)
    result = check(evidence)
    assert result.met_count < 3


def test_check_no_evidence_gives_zero_met() -> None:
    evidence = make_evidence_bundle(include_evidence=False)
    result = check(evidence)
    assert result.met_count == 0
    assert result.total_count == 3
