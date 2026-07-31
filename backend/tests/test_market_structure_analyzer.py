import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models.price_candle import PriceCandle
from app.services.smc import market_structure_analyzer
from app.services.smc.types import MarketStructureState

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _trending_candles(count: int, *, drift_per_step: float, cycle: int = 24) -> list[PriceCandle]:
    """A deterministic uptrend/downtrend: an oscillation superimposed on
    a linear drift, so it forms a clean sequence of higher (or lower)
    swing highs and lows."""
    candles = []
    for i in range(count):
        base = 100 + drift_per_step * i
        osc = math.sin(2 * math.pi * i / cycle) * 5
        mid = base + osc
        candles.append(
            PriceCandle(
                timestamp=_BASE + timedelta(hours=i),
                open=Decimal(str(mid)),
                high=Decimal(str(mid + 1)),
                low=Decimal(str(mid - 1)),
                close=Decimal(str(mid)),
            )
        )
    return candles


def test_uptrend_classified_as_bullish_with_hh_hl() -> None:
    candles = _trending_candles(150, drift_per_step=0.3)

    evidence = market_structure_analyzer.analyze(candles)

    assert evidence.state == MarketStructureState.BULLISH
    kinds = [c.kind for c in evidence.classifications]
    assert "hh" in kinds
    assert "hl" in kinds
    assert "lh" not in kinds
    assert "ll" not in kinds


def test_downtrend_classified_as_bearish_with_lh_ll() -> None:
    candles = _trending_candles(150, drift_per_step=-0.3)

    evidence = market_structure_analyzer.analyze(candles)

    assert evidence.state == MarketStructureState.BEARISH
    kinds = [c.kind for c in evidence.classifications]
    assert "lh" in kinds
    assert "ll" in kinds
    assert "hh" not in kinds
    assert "hl" not in kinds


def test_insufficient_swings_classified_as_range() -> None:
    candles = _trending_candles(5, drift_per_step=0.0)

    evidence = market_structure_analyzer.analyze(candles)

    assert evidence.state == MarketStructureState.RANGE
    assert evidence.classifications == []
