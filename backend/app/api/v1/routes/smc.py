from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.routes.market_data import get_asset_or_404
from app.dependencies.smc import get_smc_engine
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.schemas.smc import SMCAnalysisResponse, SMCMultiTimeframeResponse
from app.services.smc.types import SMCAnalysisResult, SMCMultiTimeframeResult
from app.services.smc_engine import SMCEngine

router = APIRouter(prefix="/analysis/smc", tags=["smc"])


@router.get("/{symbol}", response_model=SMCAnalysisResponse)
async def get_smc_analysis(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    engine: Annotated[SMCEngine, Depends(get_smc_engine)],
) -> SMCAnalysisResult:
    return engine.analyze(asset, timeframe)


@router.get("/{symbol}/multi-timeframe", response_model=SMCMultiTimeframeResponse)
async def get_smc_multi_timeframe_analysis(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    engine: Annotated[SMCEngine, Depends(get_smc_engine)],
) -> SMCMultiTimeframeResult:
    return engine.analyze_multi_timeframe(asset)
