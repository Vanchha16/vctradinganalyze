from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services.market_regime import pullback_reversal_analyzer
from app.services.market_regime.types import PullbackDepth, ReversalDirection
from app.services.smc.types import CHOCHEvidence, MarketStructureState, SwingClassification
from app.services.technical_analysis.types import TrendDirection

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _classification(kind: str, price: float, index: int) -> SwingClassification:
    return SwingClassification(
        kind=kind, price=Decimal(str(price)), timestamp=_BASE + timedelta(hours=index), index=index
    )


def test_healthy_pullback_in_bullish_trend() -> None:
    classifications = [_classification("hl", 90, 0), _classification("hh", 100, 5)]
    current_price = Decimal("97")  # small retracement from the high

    evidence = pullback_reversal_analyzer.analyze(
        TrendDirection.BULLISH, classifications, current_price, []
    )

    assert evidence.pullback_depth == PullbackDepth.HEALTHY
    assert evidence.retracement_ratio is not None
    assert evidence.retracement_ratio < 0.382


def test_deep_pullback_in_bullish_trend() -> None:
    classifications = [_classification("hl", 90, 0), _classification("hh", 100, 5)]
    current_price = Decimal("95")  # 50% retracement

    evidence = pullback_reversal_analyzer.analyze(
        TrendDirection.BULLISH, classifications, current_price, []
    )

    assert evidence.pullback_depth == PullbackDepth.DEEP


def test_potential_reversal_with_exhaustion_warning_when_no_choch() -> None:
    classifications = [_classification("hl", 90, 0), _classification("hh", 100, 5)]
    current_price = Decimal("91")  # ~90% retracement, no CHOCH confirming yet

    evidence = pullback_reversal_analyzer.analyze(
        TrendDirection.BULLISH, classifications, current_price, []
    )

    assert evidence.pullback_depth == PullbackDepth.POTENTIAL_REVERSAL
    assert evidence.exhaustion_warning is not None


def test_choch_confirms_reversal() -> None:
    choch = CHOCHEvidence(
        previous_trend=MarketStructureState.BULLISH,
        new_trend=MarketStructureState.BEARISH,
        confidence=0.8,
        confirmation_time=_BASE,
    )

    evidence = pullback_reversal_analyzer.analyze(
        TrendDirection.BULLISH, [], Decimal("100"), [choch]
    )

    assert evidence.reversal_direction == ReversalDirection.BEARISH
    assert evidence.reversal_confidence == 80.0
    assert evidence.exhaustion_warning is None


def test_no_classifications_returns_no_pullback_depth() -> None:
    evidence = pullback_reversal_analyzer.analyze(TrendDirection.BULLISH, [], Decimal("100"), [])

    assert evidence.pullback_depth is None
    assert evidence.retracement_ratio is None
