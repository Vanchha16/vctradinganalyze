from fastapi import APIRouter

from app.api.v1.routes import (
    analysis_confidence,
    auth,
    health,
    market_data,
    market_regime,
    news,
    smc,
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
