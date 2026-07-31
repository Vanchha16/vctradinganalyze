from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.routes.market_data import get_asset_or_404
from app.dependencies.market_regime import get_market_regime_engine
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.schemas.market_regime import MarketRegimeMultiTimeframeResponse, MarketRegimeResponse
from app.services.market_regime.types import MarketRegimeMultiTimeframeResult, MarketRegimeResult
from app.services.market_regime_engine import MarketRegimeEngine

router = APIRouter(prefix="/analysis/market-regime", tags=["market-regime"])


@router.get("/{symbol}", response_model=MarketRegimeResponse)
async def get_market_regime(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    engine: Annotated[MarketRegimeEngine, Depends(get_market_regime_engine)],
) -> MarketRegimeResult:
    return engine.analyze(asset, timeframe)


@router.get("/{symbol}/multi-timeframe", response_model=MarketRegimeMultiTimeframeResponse)
async def get_market_regime_multi_timeframe(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    engine: Annotated[MarketRegimeEngine, Depends(get_market_regime_engine)],
) -> MarketRegimeMultiTimeframeResult:
    return engine.analyze_multi_timeframe(asset)
