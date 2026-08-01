"""Deterministic spread classification (docs/12 §7, docs/48 §5,
ADR-065). `spread` is an optional caller-supplied value - never
internally sourced or fabricated, since no spread data exists anywhere
in this project. Classified as a price-relative percentage so bands are
asset-class-agnostic (no per-symbol pip table to calibrate)."""

from decimal import Decimal

from app.services.risk_management.types import SpreadClassification

_EXCELLENT_MAX = Decimal("0.0002")  # 0.02%
_ACCEPTABLE_MAX = Decimal("0.0005")  # 0.05%
_HIGH_MAX = Decimal("0.0015")  # 0.15%


def classify(spread: Decimal, entry_price: Decimal) -> SpreadClassification:
    ratio = spread / entry_price
    if ratio < _EXCELLENT_MAX:
        return SpreadClassification.EXCELLENT
    if ratio < _ACCEPTABLE_MAX:
        return SpreadClassification.ACCEPTABLE
    if ratio < _HIGH_MAX:
        return SpreadClassification.HIGH
    return SpreadClassification.EXTREME
