from decimal import Decimal

from app.services.market_regime import range_analyzer
from app.services.technical_analysis.types import (
    MovingAverageEvidence,
    SupportResistanceLevel,
    TrendDirection,
    TrendEvidence,
    TrendStrengthLevel,
)

_MOVING_AVERAGE = MovingAverageEvidence(
    price_above_ema20=None,
    price_above_ema50=None,
    price_above_ema100=None,
    price_above_ema200=None,
    price_above_sma200=None,
    bullish_alignment=False,
    bearish_alignment=False,
    alignment_score=0.0,
)


def _trend(direction: TrendDirection, strength: TrendStrengthLevel) -> TrendEvidence:
    return TrendEvidence(
        direction=direction,
        strength=strength,
        adx=None,
        di_plus=None,
        di_minus=None,
        moving_average=_MOVING_AVERAGE,
    )


def test_ranging_when_weak_trend_and_price_between_levels() -> None:
    support = SupportResistanceLevel(price=Decimal("99"), source="swing_low", strength="weak")
    resistance = SupportResistanceLevel(price=Decimal("101"), source="swing_high", strength="weak")

    evidence = range_analyzer.analyze(
        _trend(TrendDirection.SIDEWAYS, TrendStrengthLevel.WEAK),
        support,
        resistance,
        Decimal("100"),
    )

    assert evidence.is_ranging is True
    assert evidence.range_width == Decimal("2")
    assert evidence.range_strength is not None


def test_not_ranging_when_trend_is_strong() -> None:
    support = SupportResistanceLevel(price=Decimal("99"), source="swing_low", strength="weak")
    resistance = SupportResistanceLevel(price=Decimal("101"), source="swing_high", strength="weak")

    evidence = range_analyzer.analyze(
        _trend(TrendDirection.BULLISH, TrendStrengthLevel.STRONG),
        support,
        resistance,
        Decimal("100"),
    )

    assert evidence.is_ranging is False


def test_not_ranging_when_no_levels_available() -> None:
    evidence = range_analyzer.analyze(
        _trend(TrendDirection.SIDEWAYS, TrendStrengthLevel.WEAK), None, None, Decimal("100")
    )

    assert evidence.is_ranging is False
    assert evidence.range_width is None
