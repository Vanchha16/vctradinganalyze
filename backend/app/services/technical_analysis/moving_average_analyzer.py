"""docs/08 §5 Trend indicators (EMA20/50/100/200, SMA200), interpreted as
alignment facts - consumed by TrendAnalyzer, not a final verdict itself."""

from app.indicators.types import IndicatorOutput
from app.services.technical_analysis.types import MovingAverageEvidence


def analyze(indicators: dict[str, IndicatorOutput], current_price: float) -> MovingAverageEvidence:
    ema20 = indicators.get("ema_20")
    ema50 = indicators.get("ema_50")
    ema100 = indicators.get("ema_100")
    ema200 = indicators.get("ema_200")
    sma200 = indicators.get("sma_200")

    def _above(indicator: IndicatorOutput | None) -> bool | None:
        return None if indicator is None else current_price > indicator.value

    emas = [ema20, ema50, ema100, ema200]
    bullish_pairs = 0
    total_pairs = 0
    for faster, slower in zip(emas, emas[1:]):  # noqa: B905 - intentionally different lengths
        if faster is not None and slower is not None:
            total_pairs += 1
            if faster.value > slower.value:
                bullish_pairs += 1

    bullish_alignment = total_pairs == 3 and bullish_pairs == 3
    bearish_alignment = total_pairs == 3 and bullish_pairs == 0
    alignment_score = (bullish_pairs / total_pairs) if total_pairs else 0.0

    return MovingAverageEvidence(
        price_above_ema20=_above(ema20),
        price_above_ema50=_above(ema50),
        price_above_ema100=_above(ema100),
        price_above_ema200=_above(ema200),
        price_above_sma200=_above(sma200),
        bullish_alignment=bullish_alignment,
        bearish_alignment=bearish_alignment,
        alignment_score=alignment_score,
    )
