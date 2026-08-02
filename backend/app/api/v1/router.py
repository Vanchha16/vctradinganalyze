from fastapi import APIRouter

from app.api.v1.routes import (
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
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(market_data.router)
api_router.include_router(technical_analysis.router)
api_router.include_router(smc.router)
api_router.include_router(market_regime.router)
api_router.include_router(analysis_confidence.router)
api_router.include_router(news.router)
api_router.include_router(economic_calendar.router)
api_router.include_router(risk_management.router)
api_router.include_router(strategy.router)
api_router.include_router(ai_analysis.router)
api_router.include_router(signals.router)
api_router.include_router(ai_chat.router)
