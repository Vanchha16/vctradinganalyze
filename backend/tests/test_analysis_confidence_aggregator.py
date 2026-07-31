from app.services.analysis_confidence.confidence_aggregator import (
    WeightedComponent,
    combine,
    level_for,
)
from app.services.analysis_confidence.types import ConfidenceLevel

_FULL_COMPONENTS = [
    WeightedComponent("technical_alignment", 25.0),
    WeightedComponent("smc_alignment", 25.0),
    WeightedComponent("regime_confirmation", 20.0),
    WeightedComponent("cross_engine_agreement", 20.0),
    WeightedComponent("data_completeness", 5.0),
    WeightedComponent("freshness", 5.0),
]


def test_combine_sums_every_component() -> None:
    breakdown = combine(_FULL_COMPONENTS, conflict_penalty=0.0)

    assert breakdown.total == 100.0
    assert breakdown.technical_alignment == 25.0
    assert breakdown.smc_alignment == 25.0
    assert breakdown.regime_confirmation == 20.0
    assert breakdown.cross_engine_agreement == 20.0
    assert breakdown.data_completeness == 5.0
    assert breakdown.freshness == 5.0


def test_combine_floors_total_at_zero() -> None:
    breakdown = combine([WeightedComponent("technical_alignment", 5.0)], conflict_penalty=-50.0)

    assert breakdown.total == 0.0


def test_combine_caps_total_at_hundred() -> None:
    breakdown = combine([WeightedComponent("technical_alignment", 150.0)], conflict_penalty=0.0)

    assert breakdown.total == 100.0


def test_missing_component_defaults_to_zero() -> None:
    breakdown = combine([WeightedComponent("technical_alignment", 25.0)], conflict_penalty=0.0)

    assert breakdown.smc_alignment == 0.0
    assert breakdown.total == 25.0


def test_level_bands() -> None:
    assert level_for(100.0) == ConfidenceLevel.VERY_HIGH
    assert level_for(80.0) == ConfidenceLevel.VERY_HIGH
    assert level_for(79.9) == ConfidenceLevel.HIGH
    assert level_for(65.0) == ConfidenceLevel.HIGH
    assert level_for(64.9) == ConfidenceLevel.MODERATE
    assert level_for(45.0) == ConfidenceLevel.MODERATE
    assert level_for(44.9) == ConfidenceLevel.LOW
    assert level_for(25.0) == ConfidenceLevel.LOW
    assert level_for(24.9) == ConfidenceLevel.VERY_LOW
    assert level_for(0.0) == ConfidenceLevel.VERY_LOW
