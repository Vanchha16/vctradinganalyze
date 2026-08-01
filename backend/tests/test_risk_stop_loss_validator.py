from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.services.risk_management.stop_loss_validator import validate
from app.services.smc.types import (
    Direction,
    LiquiditySide,
    LiquidityZoneEvidence,
    OrderBlockEvidence,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _order_block(
    zone_low: Decimal, zone_high: Decimal, status: SMCEventStatus
) -> OrderBlockEvidence:
    return OrderBlockEvidence(
        direction=Direction.BULLISH,
        zone_high=zone_high,
        zone_low=zone_low,
        created_at=_NOW,
        status=status,
        touched=False,
        mitigated=False,
        broken=False,
        strength_score=50.0,
        freshness_score=50.0,
        volume_confirmed=True,
    )


def _liquidity_zone(level: Decimal, status: SMCEventStatus) -> LiquidityZoneEvidence:
    return LiquidityZoneEvidence(
        side=LiquiditySide.BUY_SIDE, level=level, touch_count=0, status=status, created_at=_NOW
    )


def test_validate_flags_stop_too_tight_relative_to_atr() -> None:
    result = validate(
        Decimal("1.1000"), Decimal("1.0998"), atr=0.0010, order_blocks=[], liquidity_zones=[]
    )
    assert result.too_tight is True


def test_validate_does_not_flag_reasonable_stop_distance() -> None:
    result = validate(
        Decimal("1.1000"), Decimal("1.0950"), atr=0.0010, order_blocks=[], liquidity_zones=[]
    )
    assert result.too_tight is False


def test_validate_no_atr_ratio_when_atr_unavailable() -> None:
    result = validate(
        Decimal("1.1000"), Decimal("1.0950"), atr=None, order_blocks=[], liquidity_zones=[]
    )
    assert result.atr_ratio is None
    assert result.too_tight is False


def test_validate_warns_when_stop_inside_active_order_block() -> None:
    block = _order_block(Decimal("1.0940"), Decimal("1.0960"), SMCEventStatus.ACTIVE)
    result = validate(
        Decimal("1.1000"), Decimal("1.0950"), atr=0.0010, order_blocks=[block], liquidity_zones=[]
    )
    assert any("order block" in w for w in result.warnings)


def test_validate_no_warning_for_archived_order_block() -> None:
    block = _order_block(Decimal("1.0940"), Decimal("1.0960"), SMCEventStatus.ARCHIVED)
    result = validate(
        Decimal("1.1000"), Decimal("1.0950"), atr=0.0010, order_blocks=[block], liquidity_zones=[]
    )
    assert result.warnings == []


def test_validate_warns_when_stop_near_active_liquidity_zone() -> None:
    zone = _liquidity_zone(Decimal("1.0951"), SMCEventStatus.ACTIVE)
    result = validate(
        Decimal("1.1000"), Decimal("1.0950"), atr=0.0010, order_blocks=[], liquidity_zones=[zone]
    )
    assert any("liquidity zone" in w for w in result.warnings)
