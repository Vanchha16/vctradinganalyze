"""Reframes SMC's own `smc_score` into confidence terms - does not
recompute SMC evidence, only translates its existing 0-100 score into
this engine's `smc_alignment` component.
"""

from app.services.analysis_confidence.direction_normalizer import normalize_smc_structure
from app.services.analysis_confidence.types import NormalizedDirection
from app.services.smc.types import SMCAnalysisResult

SMC_ALIGNMENT_WEIGHT = 25.0


def analyze(smc: SMCAnalysisResult | None) -> tuple[float, NormalizedDirection | None]:
    if smc is None:
        return 0.0, None

    score = (smc.smc_score / 100.0) * SMC_ALIGNMENT_WEIGHT
    return score, normalize_smc_structure(smc.market_structure.state)
