"""Maps each upstream engine's own directional vocabulary onto the
common `NormalizedDirection` axis (docs/45 §5) so alignment can be
compared meaningfully - TA's `sideways`, SMC's `range`/`transition`, and
Regime's `ranging` are conceptually equivalent but not string-equal.
"""

from app.services.analysis_confidence.types import NormalizedDirection
from app.services.smc.types import MarketStructureState
from app.services.technical_analysis.types import TrendDirection

_TECHNICAL_MAP: dict[TrendDirection, NormalizedDirection] = {
    TrendDirection.BULLISH: NormalizedDirection.BULLISH,
    TrendDirection.BEARISH: NormalizedDirection.BEARISH,
    TrendDirection.SIDEWAYS: NormalizedDirection.NEUTRAL,
}

_SMC_MAP: dict[MarketStructureState, NormalizedDirection] = {
    MarketStructureState.BULLISH: NormalizedDirection.BULLISH,
    MarketStructureState.BEARISH: NormalizedDirection.BEARISH,
    MarketStructureState.RANGE: NormalizedDirection.NEUTRAL,
    MarketStructureState.TRANSITION: NormalizedDirection.NEUTRAL,
}

# Market Regime's `trend_regime.direction` reuses TA's own `TrendDirection`
# enum directly (see `app/schemas/market_regime.py`), so the same map applies.
_REGIME_MAP = _TECHNICAL_MAP


def normalize_technical_trend(trend: TrendDirection) -> NormalizedDirection:
    return _TECHNICAL_MAP[trend]


def normalize_smc_structure(state: MarketStructureState) -> NormalizedDirection:
    return _SMC_MAP[state]


def normalize_regime_direction(direction: TrendDirection) -> NormalizedDirection:
    return _REGIME_MAP[direction]
