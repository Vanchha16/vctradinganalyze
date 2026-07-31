"""Cross-engine directional agreement (docs/45 §5) - the new evidence
this engine actually adds, distinct from each upstream engine's own
internal conflict/alignment checks. Formalizes what docs/15's original
"Agreement Score" examples gestured at without a defined formula.
"""

from collections import Counter

from app.services.analysis_confidence.types import AlignmentEvidence, NormalizedDirection

CROSS_ENGINE_AGREEMENT_WEIGHT = 20.0


def analyze(
    technical_direction: NormalizedDirection | None,
    smc_direction: NormalizedDirection | None,
    regime_direction: NormalizedDirection | None,
) -> AlignmentEvidence:
    directions = [
        d for d in (technical_direction, smc_direction, regime_direction) if d is not None
    ]

    if not directions:
        agreement_ratio = 0.0
    else:
        majority_count = Counter(directions).most_common(1)[0][1]
        agreement_ratio = majority_count / len(directions)

    return AlignmentEvidence(
        technical_direction=technical_direction,
        smc_direction=smc_direction,
        regime_direction=regime_direction,
        agreement_ratio=agreement_ratio,
        agreement_score=agreement_ratio * CROSS_ENGINE_AGREEMENT_WEIGHT,
    )
