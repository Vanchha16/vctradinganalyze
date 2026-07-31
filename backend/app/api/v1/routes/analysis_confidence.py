from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.routes.market_data import get_asset_or_404
from app.dependencies.analysis_confidence import get_analysis_confidence_engine
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.schemas.analysis_confidence import ConfidenceMultiTimeframeResponse, ConfidenceResponse
from app.services.analysis_confidence.types import ConfidenceMultiTimeframeResult, ConfidenceResult
from app.services.analysis_confidence_engine import AnalysisConfidenceEngine

router = APIRouter(prefix="/analysis/confidence", tags=["confidence"])


@router.get("/{symbol}", response_model=ConfidenceResponse)
async def get_confidence(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    engine: Annotated[AnalysisConfidenceEngine, Depends(get_analysis_confidence_engine)],
) -> ConfidenceResult:
    return engine.analyze(asset, timeframe)


@router.get("/{symbol}/multi-timeframe", response_model=ConfidenceMultiTimeframeResponse)
async def get_confidence_multi_timeframe(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    engine: Annotated[AnalysisConfidenceEngine, Depends(get_analysis_confidence_engine)],
) -> ConfidenceMultiTimeframeResult:
    return engine.analyze_multi_timeframe(asset)
