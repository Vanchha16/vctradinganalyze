from app.services.risk_management.economic_filter import EconomicFilterResult
from app.services.risk_management.types import LiquidityClassification
from app.services.strategy.requirements.scalping import check
from tests.strategy_helpers import make_evidence_bundle

_QUIET_ECONOMIC = EconomicFilterResult(economic_score=10.0, hard_reject=False, reason=None)
_LOUD_ECONOMIC = EconomicFilterResult(economic_score=0.0, hard_reject=True, reason="critical event")


def test_check_full_scalping_setup() -> None:
    evidence = make_evidence_bundle(
        liquidity=LiquidityClassification.EXCELLENT, economic=_QUIET_ECONOMIC
    )
    result = check(evidence)
    assert result.met_count == 3
    assert result.total_count == 3


def test_check_low_liquidity_reduces_matches() -> None:
    evidence = make_evidence_bundle(liquidity=LiquidityClassification.LOW, economic=_QUIET_ECONOMIC)
    result = check(evidence)
    assert result.met_count < 3


def test_check_critical_news_reduces_matches() -> None:
    evidence = make_evidence_bundle(
        liquidity=LiquidityClassification.EXCELLENT, economic=_LOUD_ECONOMIC
    )
    result = check(evidence)
    assert result.met_count < 3


def test_check_total_count_excludes_spread() -> None:
    """docs/49 §5 - Low Spread is excluded from the denominator (no
    data source, ADR-074) - only 3 requirements checked, not 4."""
    evidence = make_evidence_bundle()
    result = check(evidence)
    assert result.total_count == 3
