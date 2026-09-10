from fastapi import APIRouter, Depends

from app.api.v1.routes import (
    admin_assets,
    admin_credentials,
    admin_logs,
    admin_system,
    admin_users,
    ai_analysis,
    analysis_confidence,
    auth,
    economic_calendar,
    health,
    market_data,
    market_regime,
    metrics,
    news,
    risk_management,
    signals,
    smc,
    strategy,
    technical_analysis,
    telegram,
    watchlists,
    ws,
)
from app.config import settings
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import rate_limit_public

# Phase 9A (ADR-132) - per-IP rate limiting, applied at router-include
# time so it covers every handler on each router without touching ~30
# individual handlers. `/health*` and `/metrics` (Phase 9D, ADR-136) are
# deliberately excluded - uptime probes and scrapers must never be rate
# limited.
#
# ADR-159: the routers these decorate are no longer unauthenticated. The
# rate limit is kept anyway - it is per-IP and bounds damage from a
# single leaked or shared session, which a per-user quota does not.
_engine_rate_limit = Depends(
    rate_limit_public(
        "public_engine",
        settings.public_rate_limit_engine_limit,
        settings.public_rate_limit_window_seconds,
    )
)
_data_rate_limit = Depends(
    rate_limit_public(
        "public_data",
        settings.public_rate_limit_data_limit,
        settings.public_rate_limit_window_seconds,
    )
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(metrics.router, tags=["metrics"])
api_router.include_router(auth.router)
api_router.include_router(ws.router)
#: ADR-146: public and unauthenticated-by-session, so it carries the same
#: per-IP limit as the other public routers. It authenticates on a shared
#: secret in the path instead of a user session, but a rate limit still
#: matters here: without one, the URL - which is bearer-equivalent - could
#: be brute-forced or an obtained URL used to flood the table.
#: ADR-159 - the market data and analysis routers were readable by anyone
#: with the URL: technical analysis, SMC, regime, confidence, news,
#: calendar, prices and strategy all returned 200 unauthenticated. Applied
#: at include time for the same reason as the rate limits - one line per
#: router beats an edit to every handler, and a handler added later is
#: covered automatically rather than being public until someone notices.
#:
#: NOT applied to `health` (uptime probes), `auth` (login itself),
#: `metrics` (its own token guard, ADR-136) or `ws` (authenticates on a
#: token query parameter, since browsers cannot set WebSocket headers).
_require_auth = Depends(get_current_user)

api_router.include_router(admin_users.router)
api_router.include_router(admin_assets.router)
api_router.include_router(admin_credentials.router)
api_router.include_router(admin_logs.router)
api_router.include_router(admin_system.router)
api_router.include_router(market_data.router, dependencies=[_data_rate_limit, _require_auth])
api_router.include_router(
    technical_analysis.router, dependencies=[_engine_rate_limit, _require_auth]
)
api_router.include_router(smc.router, dependencies=[_engine_rate_limit, _require_auth])
api_router.include_router(market_regime.router, dependencies=[_engine_rate_limit, _require_auth])
api_router.include_router(
    analysis_confidence.router, dependencies=[_engine_rate_limit, _require_auth]
)
api_router.include_router(news.router, dependencies=[_data_rate_limit, _require_auth])
api_router.include_router(
    economic_calendar.router, dependencies=[_data_rate_limit, _require_auth]
)
api_router.include_router(risk_management.router, dependencies=[_engine_rate_limit, _require_auth])
api_router.include_router(strategy.router, dependencies=[_engine_rate_limit, _require_auth])
api_router.include_router(ai_analysis.router)
api_router.include_router(signals.router)
api_router.include_router(telegram.router)
api_router.include_router(watchlists.router)
