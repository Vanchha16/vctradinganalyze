"""Reframes Market Regime's own `confidence` into confidence terms -
does not recompute Regime evidence, only translates its existing 0-100
classification-reliability measure into this engine's
`regime_confirmation` component. Weighted lower than TA/SMC (docs/45 §7)
because Regime is itself derived from TA+SMC - weighting it equally
would double-count the same underlying evidence.
"""

from app.services.analysis_confidence.direction_normalizer import normalize_regime_direction
from app.services.analysis_confidence.types import NormalizedDirection
from app.services.market_regime.types import MarketRegimeResult

REGIME_CONFIRMATION_WEIGHT = 20.0


def analyze(
    market_regime: MarketRegimeResult | None,
) -> tuple[float, NormalizedDirection | None]:
    if market_regime is None:
        return 0.0, None

    score = (market_regime.confidence / 100.0) * REGIME_CONFIRMATION_WEIGHT
    return score, normalize_regime_direction(market_regime.trend_regime.direction)
