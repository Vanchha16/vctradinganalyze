from fastapi import APIRouter

from app.api.v1.routes import auth, health, market_data, technical_analysis

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(market_data.router)
api_router.include_router(technical_analysis.router)
