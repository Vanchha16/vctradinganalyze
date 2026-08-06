from fastapi import APIRouter, Depends

from app.api.v1.routes import (
    admin_logs,
    admin_system,
    admin_users,
    ai_analysis,
    ai_chat,
    analysis_confidence,
    auth,
    economic_calendar,
    health,
    market_data,
    market_regime,
    news,
    risk_management,
    signals,
    smc,
    strategy,
    technical_analysis,
    telegram,
    watchlists,
)
from app.config import settings
from app.dependencies.rate_limit import rate_limit_public

# Phase 9A (ADR-132) - per-IP rate limiting for the public, unauthenticated
# route modules (docs/60 §4.2). Applied at router-include time so it
# covers every handler on each router without touching ~30 individual
# handlers. `/health*` is deliberately excluded - uptime probes must never
# be rate limited - and every other router below already requires
# authentication (`get_current_user`/`require_admin`) or a per-user quota
# (`require_quota`), so a per-IP limit on top would be redundant.
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
api_router.include_router(auth.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_logs.router)
api_router.include_router(admin_system.router)
api_router.include_router(market_data.router, dependencies=[_data_rate_limit])
api_router.include_router(technical_analysis.router, dependencies=[_engine_rate_limit])
api_router.include_router(smc.router, dependencies=[_engine_rate_limit])
api_router.include_router(market_regime.router, dependencies=[_engine_rate_limit])
api_router.include_router(analysis_confidence.router, dependencies=[_engine_rate_limit])
api_router.include_router(news.router, dependencies=[_data_rate_limit])
api_router.include_router(economic_calendar.router, dependencies=[_data_rate_limit])
api_router.include_router(risk_management.router, dependencies=[_engine_rate_limit])
api_router.include_router(strategy.router, dependencies=[_engine_rate_limit])
api_router.include_router(ai_analysis.router)
api_router.include_router(signals.router)
api_router.include_router(ai_chat.router)
api_router.include_router(telegram.router)
api_router.include_router(watchlists.router)
