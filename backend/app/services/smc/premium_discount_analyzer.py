"""docs/09 §11 Premium & Discount Zones: always computed live from the
*current* dealing range (the most recent swing high/low pair) - unlike
every other SMC concept, this has no lifecycle and is never persisted
to `smc_events` (docs/43 §1).
"""

from collections.abc import Sequence
from decimal import Decimal

from app.models.price_candle import PriceCandle
from app.services.market_structure.swing_points import find_swing_points
from app.services.smc.types import PremiumDiscountEvidence, PremiumDiscountPosition


def analyze(candles: Sequence[PriceCandle], current_price: Decimal) -> PremiumDiscountEvidence:
    swing_highs, swing_lows = find_swing_points(candles)

    if swing_highs and swing_lows and swing_highs[-1].price > swing_lows[-1].price:
        range_high = swing_highs[-1].price
        range_low = swing_lows[-1].price
    else:
        range_high = max(c.high for c in candles)
        range_low = min(c.low for c in candles)

    equilibrium = (range_high + range_low) / 2
    range_size = range_high - range_low

    if range_size <= 0:
        return PremiumDiscountEvidence(
            position=PremiumDiscountPosition.EQUILIBRIUM,
            distance=0.0,
            range_high=range_high,
            range_low=range_low,
            equilibrium=equilibrium,
        )

    distance = float((current_price - equilibrium) / (range_size / 2))

    if current_price > equilibrium:
        position = PremiumDiscountPosition.PREMIUM
    elif current_price < equilibrium:
        position = PremiumDiscountPosition.DISCOUNT
    else:
        position = PremiumDiscountPosition.EQUILIBRIUM

    return PremiumDiscountEvidence(
        position=position,
        distance=distance,
        range_high=range_high,
        range_low=range_low,
        equilibrium=equilibrium,
    )
