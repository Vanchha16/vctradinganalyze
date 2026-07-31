"""Reframes Technical Analysis's own `technical_score` into confidence
terms - does not recompute TA evidence, only translates its existing
0-100 score into this engine's `technical_alignment` component.
"""

from app.services.analysis_confidence.direction_normalizer import normalize_technical_trend
from app.services.analysis_confidence.types import NormalizedDirection
from app.services.technical_analysis.types import TechnicalAnalysisResult

TECHNICAL_ALIGNMENT_WEIGHT = 25.0


def analyze(
    technical: TechnicalAnalysisResult | None,
) -> tuple[float, NormalizedDirection | None]:
    if technical is None:
        return 0.0, None

    score = (technical.technical_score / 100.0) * TECHNICAL_ALIGNMENT_WEIGHT
    return score, normalize_technical_trend(technical.trend)
