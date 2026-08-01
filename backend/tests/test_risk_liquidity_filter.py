from decimal import Decimal

from app.services.risk_management.liquidity_filter import classify
from app.services.risk_management.types import LiquidityClassification


def test_classify_low_below_half_average() -> None:
    assert classify(Decimal("400"), Decimal("1000")) == LiquidityClassification.LOW


def test_classify_normal_near_average() -> None:
    assert classify(Decimal("1000"), Decimal("1000")) == LiquidityClassification.NORMAL


def test_classify_high_above_1_5x() -> None:
    assert classify(Decimal("2000"), Decimal("1000")) == LiquidityClassification.HIGH


def test_classify_excellent_above_3x() -> None:
    assert classify(Decimal("3500"), Decimal("1000")) == LiquidityClassification.EXCELLENT


def test_classify_unknown_when_volume_missing() -> None:
    assert classify(None, Decimal("1000")) == LiquidityClassification.UNKNOWN


def test_classify_unknown_when_average_missing() -> None:
    assert classify(Decimal("1000"), None) == LiquidityClassification.UNKNOWN


def test_classify_unknown_when_average_zero() -> None:
    assert classify(Decimal("1000"), Decimal("0")) == LiquidityClassification.UNKNOWN
