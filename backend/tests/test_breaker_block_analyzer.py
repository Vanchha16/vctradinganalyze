from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.services.smc import breaker_block_analyzer
from app.services.smc.types import Direction, OrderBlockEvidence
from tests.smc_helpers import make_candle

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _order_block(created_index: int, zone_low: float, zone_high: float) -> OrderBlockEvidence:
    return OrderBlockEvidence(
        direction=Direction.BULLISH,
        zone_high=Decimal(str(zone_high)),
        zone_low=Decimal(str(zone_low)),
        created_at=_BASE + timedelta(hours=created_index),
        status=SMCEventStatus.ACTIVE,
        touched=False,
        mitigated=False,
        broken=False,
        strength_score=0.5,
        freshness_score=1.0,
        volume_confirmed=False,
    )


def test_order_block_invalidated_when_price_closes_through_far_side() -> None:
    ob = _order_block(0, zone_low=10.0, zone_high=12.0)
    candles = [make_candle(1, 11, 11, 8, 9)]  # closes at 9, below zone_low=10

    result = breaker_block_analyzer.analyze(candles, [ob])

    assert result[0].broken is True
    assert result[0].status == SMCEventStatus.INVALIDATED


def test_breaker_confirmed_on_retest_that_continues_in_new_direction() -> None:
    ob = _order_block(0, zone_low=10.0, zone_high=12.0)
    candles = [
        make_candle(1, 11, 11, 8, 9),  # breaks through - invalidated
        make_candle(2, 9, 11, 9, 10.5),  # retest - wicks back into the zone
        make_candle(3, 9.5, 9.5, 7, 8),  # continues down after the retest - confirmed breaker
    ]

    result = breaker_block_analyzer.analyze(candles, [ob])

    assert result[0].is_breaker is True
    assert result[0].retest_count == 1
    assert result[0].breaker_confirmed is True


def test_no_break_when_price_stays_within_zone() -> None:
    ob = _order_block(0, zone_low=10.0, zone_high=12.0)
    candles = [make_candle(1, 11, 11.5, 10.5, 11)]

    result = breaker_block_analyzer.analyze(candles, [ob])

    assert result[0].broken is False
    assert result[0].status == SMCEventStatus.ACTIVE
