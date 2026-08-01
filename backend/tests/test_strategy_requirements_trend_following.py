from app.services.strategy.requirements.trend_following import check
from tests.strategy_helpers import make_evidence_bundle


def test_check_all_requirements_met() -> None:
    evidence = make_evidence_bundle(overall_confidence=80.0)
    result = check(evidence)
    assert result.total_count == 4
    assert result.met_count == 4


def test_check_no_technical_evidence_gives_zero_met() -> None:
    evidence = make_evidence_bundle(include_evidence=False)
    result = check(evidence)
    assert result.met_count == 0
    assert result.total_count == 4


def test_check_low_confidence_reduces_met_count() -> None:
    evidence = make_evidence_bundle(overall_confidence=30.0)
    result = check(evidence)
    assert result.met_count == 3
