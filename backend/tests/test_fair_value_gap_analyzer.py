from app.models.enums import SMCEventStatus
from app.services.smc import fair_value_gap_analyzer
from app.services.smc.types import Direction
from tests.smc_helpers import make_candles


def test_bullish_fvg_detected_between_first_and_third_candle() -> None:
    specs = [
        (10, 10, 9, 10),  # first: high=10
        (10, 14, 10, 13),  # middle: displacement candle
        (13, 15, 12, 14),  # third: low=12, gap between 10 (first high) and 12 (third low)
        (14, 15, 13, 14),
        (14, 15, 13, 14),
    ]
    candles = make_candles(specs)

    gaps = fair_value_gap_analyzer.analyze(candles)

    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.direction == Direction.BULLISH
    assert float(gap.gap_low) == 10.0
    assert float(gap.gap_high) == 12.0
    assert gap.status == SMCEventStatus.ACTIVE


def test_bearish_fvg_detected_and_marked_filled_when_closed() -> None:
    specs = [
        (14, 15, 14, 14),  # first: low=14
        (14, 13, 9, 10),  # middle: displacement down
        (10, 11, 8, 9),  # third: high=11, gap between 14 (first low) and 11 (third high)
        (9, 15, 8, 14.5),  # fills the gap (closes back above 14)
    ]
    candles = make_candles(specs)

    gaps = fair_value_gap_analyzer.analyze(candles)

    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.direction == Direction.BEARISH
    assert float(gap.gap_low) == 11.0
    assert float(gap.gap_high) == 14.0
    assert gap.status == SMCEventStatus.MITIGATED


def test_no_gap_detected_without_overlap() -> None:
    specs = [(10, 11, 9, 10) for _ in range(5)]
    candles = make_candles(specs)

    assert fair_value_gap_analyzer.analyze(candles) == []
