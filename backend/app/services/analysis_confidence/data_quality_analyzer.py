"""Missing/thin-evidence detection (docs/45 §5) - were all three engines
able to run, and did they find substantive evidence (support/resistance
levels, SMC structural events, a qualifying regime candidate) or fall
back to an empty/uncertain result.
"""

from app.services.analysis_confidence.types import DataQualityEvidence
from app.services.market_regime.types import MarketRegimeResult, MarketRegimeState
from app.services.smc.types import SMCAnalysisResult
from app.services.technical_analysis.types import TechnicalAnalysisResult

DATA_COMPLETENESS_WEIGHT = 5.0

# Each missing signal costs an equal share of the total weight.
_SIGNALS = (
    "technical_analysis_unavailable",
    "smc_unavailable",
    "market_regime_unavailable",
    "no_support_resistance_levels",
    "smc_no_structural_evidence",
    "market_regime_uncertain",
)
_PENALTY_PER_SIGNAL = DATA_COMPLETENESS_WEIGHT / len(_SIGNALS)


def analyze(
    technical: TechnicalAnalysisResult | None,
    smc: SMCAnalysisResult | None,
    market_regime: MarketRegimeResult | None,
) -> DataQualityEvidence:
    missing: list[str] = []

    if technical is None:
        missing.append("technical_analysis_unavailable")
    elif technical.support is None and technical.resistance is None:
        missing.append("no_support_resistance_levels")

    if smc is None:
        missing.append("smc_unavailable")
    elif not (
        smc.bos
        or smc.choch
        or smc.order_blocks
        or smc.fair_value_gaps
        or smc.liquidity_zones
        or smc.liquidity_sweeps
    ):
        missing.append("smc_no_structural_evidence")

    if market_regime is None:
        missing.append("market_regime_unavailable")
    elif market_regime.regime == MarketRegimeState.UNCERTAIN:
        missing.append("market_regime_uncertain")

    completeness_score = max(0.0, DATA_COMPLETENESS_WEIGHT - (_PENALTY_PER_SIGNAL * len(missing)))
    return DataQualityEvidence(missing_data=missing, completeness_score=completeness_score)
