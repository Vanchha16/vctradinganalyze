from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.routes.market_data import get_asset_or_404
from app.dependencies import get_technical_analysis_engine
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.schemas.technical_analysis import MultiTimeframeAnalysisResponse, TechnicalAnalysisResponse
from app.services.technical_analysis.types import MultiTimeframeResult, TechnicalAnalysisResult
from app.services.technical_analysis_engine import TechnicalAnalysisEngine

router = APIRouter(prefix="/analysis/technical", tags=["technical-analysis"])


@router.get("/{symbol}", response_model=TechnicalAnalysisResponse)
async def get_technical_analysis(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    engine: Annotated[TechnicalAnalysisEngine, Depends(get_technical_analysis_engine)],
) -> TechnicalAnalysisResult:
    return engine.analyze(asset, timeframe)


@router.get("/{symbol}/multi-timeframe", response_model=MultiTimeframeAnalysisResponse)
async def get_multi_timeframe_analysis(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    engine: Annotated[TechnicalAnalysisEngine, Depends(get_technical_analysis_engine)],
) -> MultiTimeframeResult:
    return engine.analyze_multi_timeframe(asset)
