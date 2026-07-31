"""Regime-level conflict detection, mirroring Technical Analysis's
`ConflictAnalyzer` pattern (docs/42 §8) - each contradiction becomes a
penalty on `RegimeConfidenceBreakdown`, not a verdict override.
"""

from app.services.market_regime.types import (
    AccumulationDistributionEvidence,
    RangeEvidence,
    RegimeConflict,
    RegimeConflictReport,
    TrendRegimeEvidence,
)
from app.services.technical_analysis.types import TrendStrengthLevel

_STRUCTURE_SCORE_THRESHOLD = 50.0


def analyze(
    trend_regime: TrendRegimeEvidence,
    range_evidence: RangeEvidence,
    accumulation_distribution: AccumulationDistributionEvidence,
) -> RegimeConflictReport:
    conflicts: list[RegimeConflict] = []

    strong_trend = trend_regime.strength in (
        TrendStrengthLevel.STRONG,
        TrendStrengthLevel.VERY_STRONG,
    )
    if strong_trend and range_evidence.is_ranging:
        conflicts.append(RegimeConflict("Strong trend evidence and range evidence disagree"))

    if not trend_regime.aligned:
        conflicts.append(
            RegimeConflict("Technical Analysis trend and SMC market structure disagree")
        )

    if (
        accumulation_distribution.accumulation_score >= _STRUCTURE_SCORE_THRESHOLD
        and accumulation_distribution.distribution_score >= _STRUCTURE_SCORE_THRESHOLD
    ):
        conflicts.append(RegimeConflict("Both accumulation and distribution evidence present"))

    return RegimeConflictReport(conflicts=conflicts)
