from decimal import Decimal

import pytest

from app.services.risk_management.spread_filter import classify
from app.services.risk_management.types import SpreadClassification


@pytest.mark.parametrize(
    ("spread", "entry_price", "expected"),
    [
        (Decimal("0.00010"), Decimal("1.10000"), SpreadClassification.EXCELLENT),
        (Decimal("0.00040"), Decimal("1.10000"), SpreadClassification.ACCEPTABLE),
        (Decimal("0.00100"), Decimal("1.10000"), SpreadClassification.HIGH),
        (Decimal("0.00300"), Decimal("1.10000"), SpreadClassification.EXTREME),
    ],
)
def test_classify_matches_bands(
    spread: Decimal, entry_price: Decimal, expected: SpreadClassification
) -> None:
    assert classify(spread, entry_price) == expected
