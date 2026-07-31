"""Combines every component's weighted contribution into one
`ConfidenceBreakdown` (docs/45 §9). Deliberately built around a generic,
named-component list (`combine`) rather than positional arguments, so
Phase 5/6 (News Sentiment, Economic Calendar, Risk Management - docs/15
§3's deferred inputs) can add new weighted components by extending the
component list and `ConfidenceBreakdown`'s fields, without restructuring
how components are summed/floored/capped here.
"""

from dataclasses import dataclass

from app.services.analysis_confidence.types import ConfidenceBreakdown, ConfidenceLevel

#: docs/45 §6 - starting-point bands, not tuned against real outcomes yet.
_LEVEL_BANDS: tuple[tuple[float, ConfidenceLevel], ...] = (
    (80.0, ConfidenceLevel.VERY_HIGH),
    (65.0, ConfidenceLevel.HIGH),
    (45.0, ConfidenceLevel.MODERATE),
    (25.0, ConfidenceLevel.LOW),
    (0.0, ConfidenceLevel.VERY_LOW),
)


@dataclass(frozen=True, slots=True)
class WeightedComponent:
    """One named, independently-computed contribution to overall
    confidence. Adding a new evidence source (Phase 5/6) means
    constructing one more of these, not changing `combine`."""

    name: str
    score: float


def combine(components: list[WeightedComponent], conflict_penalty: float) -> ConfidenceBreakdown:
    values = {component.name: component.score for component in components}

    return ConfidenceBreakdown(
        technical_alignment=values.get("technical_alignment", 0.0),
        smc_alignment=values.get("smc_alignment", 0.0),
        regime_confirmation=values.get("regime_confirmation", 0.0),
        cross_engine_agreement=values.get("cross_engine_agreement", 0.0),
        data_completeness=values.get("data_completeness", 0.0),
        freshness=values.get("freshness", 0.0),
        conflict_penalty=conflict_penalty,
    )


def level_for(total: float) -> ConfidenceLevel:
    for threshold, level in _LEVEL_BANDS:
        if total >= threshold:
            return level
    return ConfidenceLevel.VERY_LOW
