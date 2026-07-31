from decimal import Decimal

from app.services.smc import premium_discount_analyzer
from app.services.smc.types import PremiumDiscountPosition
from tests.smc_helpers import make_candles


def _range_candles() -> list:
    # A clean V then ^ - swing low at 90 (index~3), swing high at 110 (index~9).
    specs = [
        (100, 101, 99, 100),
        (95, 96, 92, 94),
        (92, 93, 91, 92),
        (91, 92, 90, 91),  # swing low: 90
        (93, 95, 91, 94),
        (98, 100, 95, 99),
        (103, 106, 100, 104),
        (107, 109, 103, 108),
        (109, 110.5, 106, 109),
        (108, 110, 105, 107),  # swing high: 110.5 around here
        (105, 106, 100, 103),
        (100, 101, 96, 98),
        (96, 97, 93, 95),
    ]
    return make_candles(specs)


def test_price_in_discount_zone() -> None:
    candles = _range_candles()

    evidence = premium_discount_analyzer.analyze(candles, current_price=Decimal("92"))

    assert evidence.position == PremiumDiscountPosition.DISCOUNT
    assert evidence.distance < 0


def test_price_in_premium_zone() -> None:
    candles = _range_candles()

    evidence = premium_discount_analyzer.analyze(candles, current_price=Decimal("108"))

    assert evidence.position == PremiumDiscountPosition.PREMIUM
    assert evidence.distance > 0


def test_flat_range_returns_equilibrium() -> None:
    specs = [(100, 100, 100, 100) for _ in range(5)]
    candles = make_candles(specs)

    evidence = premium_discount_analyzer.analyze(candles, current_price=Decimal("100"))

    assert evidence.position == PremiumDiscountPosition.EQUILIBRIUM
    assert evidence.distance == 0.0
