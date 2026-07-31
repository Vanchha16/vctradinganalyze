"""Freshness scoring (docs/45 §5) - how recent is each available
engine's `calculated_at` relative to a timeframe-appropriate staleness
threshold. Low weight by design: in this project's current architecture
every engine is stateless-and-computed-on-demand (or, for SMC,
persisted but always recomputed fresh per request) from stored candles,
so freshness mostly reflects the market-data pipeline's own polling
cadence, not something this engine controls - it is diagnostic evidence,
not a strong quality signal yet (docs/45 §7).
"""

from datetime import UTC, datetime, timedelta

from app.models.enums import Timeframe
from app.services.analysis_confidence.types import FreshnessEvidence
from app.services.market_regime.types import MarketRegimeResult
from app.services.smc.types import SMCAnalysisResult
from app.services.technical_analysis.types import TechnicalAnalysisResult

FRESHNESS_WEIGHT = 5.0

#: Starting-point thresholds (docs/45 §7's usual caveat: not tuned
#: against real request patterns yet). A result is "stale" once its
#: `calculated_at` is older than the candle interval it represents, with
#: generous headroom for normal polling latency.
STALENESS_THRESHOLDS: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=5),
    Timeframe.M5: timedelta(minutes=15),
    Timeframe.M15: timedelta(minutes=30),
    Timeframe.M30: timedelta(hours=1),
    Timeframe.H1: timedelta(hours=2),
    Timeframe.H4: timedelta(hours=8),
    Timeframe.D1: timedelta(days=2),
    Timeframe.W1: timedelta(days=9),
    Timeframe.MN: timedelta(days=35),
}


def analyze(
    technical: TechnicalAnalysisResult | None,
    smc: SMCAnalysisResult | None,
    market_regime: MarketRegimeResult | None,
    timeframe: Timeframe,
    now: datetime,
) -> FreshnessEvidence:
    threshold = STALENESS_THRESHOLDS[timeframe]

    timestamps = [
        _as_aware_utc(result.calculated_at)
        for result in (technical, smc, market_regime)
        if result is not None
    ]
    is_stale = any((now - ts) > threshold for ts in timestamps)

    if not timestamps:
        freshness_score = 0.0
    elif is_stale:
        freshness_score = FRESHNESS_WEIGHT * 0.5
    else:
        freshness_score = FRESHNESS_WEIGHT

    return FreshnessEvidence(
        technical_calculated_at=technical.calculated_at if technical is not None else None,
        smc_calculated_at=smc.calculated_at if smc is not None else None,
        regime_calculated_at=market_regime.calculated_at if market_regime is not None else None,
        is_stale=is_stale,
        freshness_score=freshness_score,
    )


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes for `DateTime(timezone=True)`
    columns even though they were written UTC-aware (BACKLOG.md §9,
    institutional knowledge) - candle timestamps flow into
    `calculated_at` on every upstream engine, so this comparison hits
    the same gotcha `AuthenticationService._as_aware_utc` was added for."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
