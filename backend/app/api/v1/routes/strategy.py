from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.routes.market_data import get_asset_or_404
from app.dependencies.strategy import get_strategy_engine
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.schemas.strategy import StrategyEvaluationResponse
from app.services.strategy_engine import StrategyEngine

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.get("/evaluate/{symbol}", response_model=StrategyEvaluationResponse)
async def evaluate_strategy(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    engine: Annotated[StrategyEngine, Depends(get_strategy_engine)],
) -> StrategyEvaluationResponse:
    evaluation = engine.evaluate(asset, timeframe)
    return StrategyEvaluationResponse.model_validate(evaluation)
