"""Factory functions for building `StrategyEvidenceBundle` fixtures for
Strategy Engine unit tests - reuses `analysis_confidence_helpers`'s
`make_technical_result`/`make_smc_result`/`make_regime_result`."""

from app.services.market_regime.types import MarketRegimeResult
from app.services.risk_management.economic_filter import EconomicFilterResult
from app.services.risk_management.types import LiquidityClassification, MarketSession
from app.services.smc.types import SMCAnalysisResult
from app.services.strategy.types import StrategyEvidenceBundle
from app.services.technical_analysis.types import TechnicalAnalysisResult
from tests.analysis_confidence_helpers import (
    make_regime_result,
    make_smc_result,
    make_technical_result,
)

_NEUTRAL_ECONOMIC = EconomicFilterResult(economic_score=10.0, hard_reject=False, reason=None)


def make_evidence_bundle(
    *,
    technical: TechnicalAnalysisResult | None = None,
    smc: SMCAnalysisResult | None = None,
    market_regime: MarketRegimeResult | None = None,
    overall_confidence: float = 70.0,
    session: MarketSession = MarketSession.LONDON,
    liquidity: LiquidityClassification = LiquidityClassification.NORMAL,
    economic: EconomicFilterResult = _NEUTRAL_ECONOMIC,
    include_evidence: bool = True,
) -> StrategyEvidenceBundle:
    if include_evidence:
        technical = technical if technical is not None else make_technical_result()
        smc = smc if smc is not None else make_smc_result()
        market_regime = market_regime if market_regime is not None else make_regime_result()

    return StrategyEvidenceBundle(
        technical=technical,
        smc=smc,
        market_regime=market_regime,
        overall_confidence=overall_confidence,
        session=session,
        liquidity=liquidity,
        economic=economic,
    )
