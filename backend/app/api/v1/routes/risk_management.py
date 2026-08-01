from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.market_data import get_asset_repository
from app.dependencies.risk_management import get_risk_management_engine
from app.exceptions import ResourceNotFoundException
from app.repositories.asset_repository import AssetRepository
from app.schemas.risk_management import RiskEvaluationRequest, RiskEvaluationResponse
from app.services.risk_management_engine import RiskManagementEngine

router = APIRouter(prefix="/risk", tags=["risk-management"])


@router.post("/evaluate", response_model=RiskEvaluationResponse)
async def evaluate_risk(
    request: RiskEvaluationRequest,
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
    engine: Annotated[RiskManagementEngine, Depends(get_risk_management_engine)],
) -> RiskEvaluationResponse:
    asset = asset_repository.get_by_symbol(request.symbol.upper())
    if asset is None:
        raise ResourceNotFoundException(f"Unknown asset symbol: {request.symbol.upper()}")

    evaluation = engine.evaluate(
        asset,
        request.timeframe,
        request.direction,
        request.entry_price,
        request.stop_loss,
        request.take_profit,
        spread=request.spread,
    )
    return RiskEvaluationResponse.model_validate(evaluation)
