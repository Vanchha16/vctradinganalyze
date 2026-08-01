"""Deterministic liquidity classification via a relative-volume-ratio
proxy (docs/12 §10, docs/48 §5, ADR-066). No order-book/market-depth
data source exists in this project - `UNKNOWN` when volume is
unavailable, mirroring Technical Analysis's `VolumeState.UNAVAILABLE`
precedent, never fabricated."""

from decimal import Decimal

from app.services.risk_management.types import LiquidityClassification

_LOW_MAX_RATIO = Decimal("0.5")
_NORMAL_MAX_RATIO = Decimal("1.5")
_HIGH_MAX_RATIO = Decimal("3.0")


def classify(
    latest_volume: Decimal | None, recent_average_volume: Decimal | None
) -> LiquidityClassification:
    if latest_volume is None or recent_average_volume is None or recent_average_volume == 0:
        return LiquidityClassification.UNKNOWN

    ratio = latest_volume / recent_average_volume
    if ratio < _LOW_MAX_RATIO:
        return LiquidityClassification.LOW
    if ratio < _NORMAL_MAX_RATIO:
        return LiquidityClassification.NORMAL
    if ratio < _HIGH_MAX_RATIO:
        return LiquidityClassification.HIGH
    return LiquidityClassification.EXCELLENT
