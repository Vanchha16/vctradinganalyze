"""docs/16 §6 Trend Detection: combines Technical Analysis's ADX/EMA
verdict (`TrendEvidence`) with SMC's HH/HL/LH/LL structure
(`MarketStructureEvidence`) - both already computed upstream, so this
analyzer only checks agreement, it never re-derives either fact.
"""

from app.services.market_regime.types import TrendRegimeEvidence
from app.services.smc.types import MarketStructureEvidence, MarketStructureState
from app.services.technical_analysis.types import TrendDirection, TrendEvidence


def analyze(
    trend_evidence: TrendEvidence, market_structure: MarketStructureEvidence
) -> TrendRegimeEvidence:
    aligned = (
        trend_evidence.direction == TrendDirection.BULLISH
        and market_structure.state == MarketStructureState.BULLISH
    ) or (
        trend_evidence.direction == TrendDirection.BEARISH
        and market_structure.state == MarketStructureState.BEARISH
    )

    return TrendRegimeEvidence(
        direction=trend_evidence.direction,
        strength=trend_evidence.strength,
        structure_state=market_structure.state,
        aligned=aligned,
    )
