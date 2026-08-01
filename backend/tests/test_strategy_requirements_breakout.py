from dataclasses import replace

from app.services.market_regime.types import BreakoutDirection, BreakoutEvidence, MarketRegimeResult
from app.services.strategy.requirements.breakout import check
from tests.analysis_confidence_helpers import make_regime_result
from tests.strategy_helpers import make_evidence_bundle


def _regime_with_breakout(*, detected: bool, volume_confirmed: bool) -> MarketRegimeResult:
    regime = make_regime_result()
    return replace(
        regime,
        breakout=BreakoutEvidence(
            detected=detected,
            direction=BreakoutDirection.BULLISH if detected else None,
            volume_confirmed=volume_confirmed,
        ),
    )


def test_check_full_breakout_setup() -> None:
    regime = _regime_with_breakout(detected=True, volume_confirmed=True)
    evidence = make_evidence_bundle(market_regime=regime)
    result = check(evidence)
    assert result.met_count == 4
    assert result.total_count == 4


def test_check_no_breakout_detected() -> None:
    regime = _regime_with_breakout(detected=False, volume_confirmed=False)
    evidence = make_evidence_bundle(market_regime=regime)
    result = check(evidence)
    assert result.met_count < 4


def test_check_no_evidence_gives_zero_met() -> None:
    evidence = make_evidence_bundle(include_evidence=False)
    result = check(evidence)
    assert result.met_count == 0
    assert result.total_count == 4
