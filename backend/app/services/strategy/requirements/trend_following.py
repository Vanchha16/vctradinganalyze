"""Trend Following requirements checklist (docs/17 §7, docs/49 §5).
EMA alignment, strong ADX, healthy volume, high confidence - all
already-computed evidence, no new calculation."""

from app.services.strategy.types import RequirementsResult, StrategyEvidenceBundle
from app.services.technical_analysis.types import VolumeState

_STRONG_ADX_THRESHOLD = 25.0
_HIGH_CONFIDENCE_THRESHOLD = 65.0


def check(evidence: StrategyEvidenceBundle) -> RequirementsResult:
    if evidence.technical is None:
        return RequirementsResult(met_count=0, total_count=4)

    moving_average = evidence.technical.trend_evidence.moving_average
    ema_aligned = moving_average.bullish_alignment or moving_average.bearish_alignment

    adx = evidence.technical.trend_evidence.adx
    strong_adx = adx is not None and adx >= _STRONG_ADX_THRESHOLD

    healthy_volume = evidence.technical.volume.relative_volume_state is VolumeState.ABOVE_AVERAGE

    high_confidence = evidence.overall_confidence >= _HIGH_CONFIDENCE_THRESHOLD

    met_count = sum([ema_aligned, strong_adx, healthy_volume, high_confidence])
    return RequirementsResult(met_count=met_count, total_count=4)
