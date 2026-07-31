from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.enums import SMCEventStatus
from app.services.smc import mitigation_analyzer
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


def test_order_block_touched_when_wick_enters_zone() -> None:
    ob = _order_block(0, zone_low=10.0, zone_high=12.0)
    # Later candle wicks into [10, 12] but closes above it.
    candles = [make_candle(1, 13, 14, 11, 13)]

    result = mitigation_analyzer.analyze(candles, [ob])

    assert result[0].touched is True
    assert result[0].mitigated is False
    assert result[0].status == SMCEventStatus.ACTIVE


def test_order_block_mitigated_when_candle_closes_within_zone() -> None:
    ob = _order_block(0, zone_low=10.0, zone_high=12.0)
    candles = [make_candle(1, 13, 14, 10.5, 11.0)]  # closes at 11, inside [10, 12]

    result = mitigation_analyzer.analyze(candles, [ob])

    assert result[0].touched is True
    assert result[0].mitigated is True
    assert result[0].status == SMCEventStatus.MITIGATED


def test_candles_before_creation_are_ignored() -> None:
    ob = _order_block(5, zone_low=10.0, zone_high=12.0)
    candles = [make_candle(1, 11, 11, 10.5, 11.0)]  # occurs before the zone was created

    result = mitigation_analyzer.analyze(candles, [ob])

    assert result[0].touched is False
    assert result[0].mitigated is False
