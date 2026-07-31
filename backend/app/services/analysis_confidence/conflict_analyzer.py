"""Cross-engine contradiction detection (docs/45 §5), distinct from each
upstream engine's own internal conflict analyzer (TA's `ConflictAnalyzer`,
SMC's `conflict_analyzer`, Regime's `conflict_analyzer` each detect
conflicts *within* their own evidence; this one detects disagreement
*between* engines). Each rule is independently testable and returns a
structured `ConflictEvidence`, never a bare string.

Does not independently penalize volatility - Market Regime's
`confidence_breakdown.volatility_clarity` already scores it (reused via
`regime_confidence_analyzer`), and double-penalizing the same underlying
market condition here would silently double-count it (docs/45 §7).
"""

from app.services.analysis_confidence.direction_normalizer import (
    normalize_smc_structure,
    normalize_technical_trend,
)
from app.services.analysis_confidence.types import (
    AlignmentEvidence,
    ConflictEvidence,
    ConflictSeverity,
    NormalizedDirection,
)
from app.services.market_regime.types import MarketRegimeResult
from app.services.smc.types import SMCAnalysisResult
from app.services.technical_analysis.types import TechnicalAnalysisResult

CONFLICT_PENALTY_WEIGHT = -15.0
_PENALTY_PER_SEVERITY = {
    ConflictSeverity.LOW: 3.0,
    ConflictSeverity.MEDIUM: 6.0,
    ConflictSeverity.HIGH: 10.0,
}

_SCORE_QUARTILE_GAP = 50.0  # points apart on their respective 0-100 scales


def analyze(
    technical: TechnicalAnalysisResult | None,
    smc: SMCAnalysisResult | None,
    market_regime: MarketRegimeResult | None,
    alignment: AlignmentEvidence,
) -> list[ConflictEvidence]:
    conflicts: list[ConflictEvidence] = []

    ta_smc = _check_technical_smc_direction_conflict(technical, smc)
    if ta_smc is not None:
        conflicts.append(ta_smc)

    regime_internal = _check_regime_internal_alignment(market_regime)
    if regime_internal is not None:
        conflicts.append(regime_internal)

    score_mismatch = _check_score_quartile_mismatch(technical, smc)
    if score_mismatch is not None:
        conflicts.append(score_mismatch)

    regime_vs_majority = _check_regime_against_majority(market_regime, alignment)
    if regime_vs_majority is not None:
        conflicts.append(regime_vs_majority)

    return conflicts


def penalty_for(conflicts: list[ConflictEvidence]) -> float:
    raw = -sum(_PENALTY_PER_SEVERITY[c.severity] for c in conflicts)
    return max(CONFLICT_PENALTY_WEIGHT, raw)


def overall_severity(conflicts: list[ConflictEvidence]) -> ConflictSeverity:
    if not conflicts:
        return ConflictSeverity.NONE
    severities = [c.severity for c in conflicts]
    if ConflictSeverity.HIGH in severities:
        return ConflictSeverity.HIGH
    if ConflictSeverity.MEDIUM in severities:
        return ConflictSeverity.MEDIUM
    return ConflictSeverity.LOW


def _check_technical_smc_direction_conflict(
    technical: TechnicalAnalysisResult | None, smc: SMCAnalysisResult | None
) -> ConflictEvidence | None:
    if technical is None or smc is None:
        return None

    technical_direction = normalize_technical_trend(technical.trend)
    smc_direction = normalize_smc_structure(smc.market_structure.state)
    if {technical_direction, smc_direction} == {
        NormalizedDirection.BULLISH,
        NormalizedDirection.BEARISH,
    }:
        return ConflictEvidence(
            description=(
                f"Technical Analysis trend ({technical.trend}) contradicts "
                f"SMC market structure ({smc.market_structure.state})."
            ),
            severity=ConflictSeverity.HIGH,
            engines_involved=["technical_analysis", "smc"],
        )
    return None


def _check_regime_internal_alignment(
    market_regime: MarketRegimeResult | None,
) -> ConflictEvidence | None:
    if market_regime is None or market_regime.trend_regime.aligned:
        return None

    return ConflictEvidence(
        description=(
            "Market Regime's own trend/structure evidence disagree "
            f"(structure_state={market_regime.trend_regime.structure_state})."
        ),
        severity=ConflictSeverity.MEDIUM,
        engines_involved=["market_regime"],
    )


def _check_regime_against_majority(
    market_regime: MarketRegimeResult | None, alignment: AlignmentEvidence
) -> ConflictEvidence | None:
    """Regime's direction opposing the TA/SMC majority is a distinct
    signal from `_check_technical_smc_direction_conflict` above - it
    reads `alignment`'s already-computed majority rather than
    re-deriving TA-vs-SMC directly."""
    if market_regime is None or alignment.regime_direction is None:
        return None

    other_directions = [
        d for d in (alignment.technical_direction, alignment.smc_direction) if d is not None
    ]
    if len(other_directions) < 2:
        return None

    if (
        other_directions[0] == other_directions[1]
        and other_directions[0] != NormalizedDirection.NEUTRAL
        and alignment.regime_direction != other_directions[0]
        and alignment.regime_direction != NormalizedDirection.NEUTRAL
    ):
        return ConflictEvidence(
            description=(
                f"Market Regime direction ({market_regime.trend_regime.direction}) opposes the "
                "Technical Analysis/SMC majority direction."
            ),
            severity=ConflictSeverity.LOW,
            engines_involved=["market_regime", "technical_analysis", "smc"],
        )
    return None


def _check_score_quartile_mismatch(
    technical: TechnicalAnalysisResult | None, smc: SMCAnalysisResult | None
) -> ConflictEvidence | None:
    if technical is None or smc is None:
        return None

    gap = abs(technical.technical_score - smc.smc_score)
    if gap >= _SCORE_QUARTILE_GAP:
        return ConflictEvidence(
            description=(
                f"Technical Analysis score ({technical.technical_score:.1f}) and SMC score "
                f"({smc.smc_score:.1f}) diverge sharply."
            ),
            severity=ConflictSeverity.MEDIUM,
            engines_involved=["technical_analysis", "smc"],
        )
    return None
