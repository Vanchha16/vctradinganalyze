"""docs/09 §10 Liquidity: equal highs/lows within a magnitude-aware
tolerance (ADR-035 - 5 basis points of price, not a fixed absolute
value, so it generalizes across forex pairs, indices, and gold/crypto
price scales alike). Two or more swing highs within tolerance form a
buy-side liquidity zone; swing lows form sell-side. A sweep is a wick
beyond the level that *closes back inside* it - the mirror image of a
BOS, which closes beyond.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.models.price_candle import PriceCandle
from app.services.market_structure.swing_points import SwingPoint, find_swing_points
from app.services.smc.types import LiquiditySide, LiquiditySweepEvidence, LiquidityZoneEvidence

_TOLERANCE_RATIO = Decimal("0.0005")


def _group_equal_levels(points: Sequence[SwingPoint]) -> list[list[SwingPoint]]:
    if not points:
        return []
    ordered = sorted(points, key=lambda p: p.price)
    groups: list[list[SwingPoint]] = [[ordered[0]]]
    for point in ordered[1:]:
        reference = groups[-1][0].price
        tolerance = reference * _TOLERANCE_RATIO
        if abs(point.price - reference) <= tolerance:
            groups[-1].append(point)
        else:
            groups.append([point])
    return [group for group in groups if len(group) >= 2]


def _zones(groups: list[list[SwingPoint]], side: LiquiditySide) -> list[LiquidityZoneEvidence]:
    zones = []
    for group in groups:
        level = (
            max(p.price for p in group)
            if side == LiquiditySide.BUY_SIDE
            else min(p.price for p in group)
        )
        created_at = min(p.timestamp for p in group)
        zones.append(
            LiquidityZoneEvidence(
                side=side,
                level=level,
                touch_count=len(group),
                status=SMCEventStatus.ACTIVE,
                created_at=created_at,
            )
        )
    return zones


def _sweeps(
    candles: Sequence[PriceCandle], zones: list[LiquidityZoneEvidence]
) -> list[LiquiditySweepEvidence]:
    sweeps = []
    for zone in zones:
        for candle in candles:
            if candle.timestamp <= zone.created_at:
                continue
            if (
                zone.side == LiquiditySide.BUY_SIDE
                and candle.high > zone.level
                and candle.close < zone.level
            ):
                sweeps.append(
                    LiquiditySweepEvidence(
                        side=zone.side,
                        level=zone.level,
                        sweep_time=candle.timestamp,
                        false_breakout=True,
                    )
                )
                break
            if (
                zone.side == LiquiditySide.SELL_SIDE
                and candle.low < zone.level
                and candle.close > zone.level
            ):
                sweeps.append(
                    LiquiditySweepEvidence(
                        side=zone.side,
                        level=zone.level,
                        sweep_time=candle.timestamp,
                        false_breakout=True,
                    )
                )
                break
    return sweeps


def analyze(
    candles: Sequence[PriceCandle],
) -> tuple[list[LiquidityZoneEvidence], list[LiquiditySweepEvidence]]:
    swing_highs, swing_lows = find_swing_points(candles)

    buy_side_zones = _zones(_group_equal_levels(swing_highs), LiquiditySide.BUY_SIDE)
    sell_side_zones = _zones(_group_equal_levels(swing_lows), LiquiditySide.SELL_SIDE)
    all_zones = buy_side_zones + sell_side_zones

    sweeps = _sweeps(candles, all_zones)

    return all_zones, sweeps
