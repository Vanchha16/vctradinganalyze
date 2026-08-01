"""Deterministic stop-loss validation (docs/12 §13, docs/48 §6). The
ATR-distance check is the only hard-reject rule here (ADR-068); the
Order Block / Liquidity Zone proximity checks are informational-only
(docs/12 §13's own softer "check" framing), reusing SMC's already-
computed structure (`app.services.smc.types`) rather than a new
structural-invalidation algorithm docs/12 doesn't fully specify."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.services.smc.types import LiquidityZoneEvidence, OrderBlockEvidence

_MIN_ATR_RATIO = Decimal("0.5")
_LIQUIDITY_ZONE_PROXIMITY_RATIO = Decimal("0.1")  # fraction of ATR


@dataclass(frozen=True, slots=True)
class StopLossValidationResult:
    atr_ratio: float | None
    too_tight: bool
    warnings: list[str] = field(default_factory=list)


def validate(
    entry_price: Decimal,
    stop_loss: Decimal,
    atr: float | None,
    order_blocks: Sequence[OrderBlockEvidence],
    liquidity_zones: Sequence[LiquidityZoneEvidence],
) -> StopLossValidationResult:
    distance = abs(entry_price - stop_loss)
    warnings: list[str] = []

    atr_ratio: float | None = None
    too_tight = False
    if atr is not None and atr > 0:
        atr_decimal = Decimal(str(atr))
        atr_ratio = float(distance / atr_decimal)
        too_tight = distance < _MIN_ATR_RATIO * atr_decimal

        proximity = _LIQUIDITY_ZONE_PROXIMITY_RATIO * atr_decimal
        for zone in liquidity_zones:
            if zone.status is SMCEventStatus.ACTIVE and abs(stop_loss - zone.level) <= proximity:
                warnings.append(
                    f"Stop-loss is near an active liquidity zone at {zone.level} - "
                    "may be vulnerable to a sweep."
                )

    for block in order_blocks:
        if block.status is SMCEventStatus.ACTIVE and block.zone_low <= stop_loss <= block.zone_high:
            warnings.append(
                f"Stop-loss sits inside an active order block [{block.zone_low}, "
                f"{block.zone_high}] - consider a more structural placement."
            )

    return StopLossValidationResult(atr_ratio=atr_ratio, too_tight=too_tight, warnings=warnings)
