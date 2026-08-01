from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.routes.market_data import get_asset_or_404
from app.dependencies import get_current_user
from app.dependencies.ai_orchestrator import get_ai_analysis_repository, get_ai_orchestrator_engine
from app.dependencies.market_data import get_asset_repository
from app.exceptions import ResourceNotFoundException
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import Timeframe
from app.models.user import User
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.asset_repository import AssetRepository
from app.schemas.ai_analysis import AIAnalysisListResponse, AIAnalysisResponse, ReasoningResponse
from app.services.ai_orchestrator.types import AIAnalysisResult
from app.services.ai_orchestrator_engine import AIOrchestratorEngine

router = APIRouter(tags=["ai-analysis"])


def _result_to_response(result: AIAnalysisResult) -> AIAnalysisResponse:
    return AIAnalysisResponse(
        id=result.id,
        symbol=result.symbol,
        timeframe=result.timeframe,
        recommendation=result.recommendation,
        confidence_score=result.confidence_score,
        confidence_level=result.confidence_level,
        risk_level=result.risk_level,
        entry_price=result.entry_price,
        stop_loss=result.stop_loss,
        take_profit=result.take_profit,
        execution_guidance=result.execution_guidance,
        reasoning=ReasoningResponse.model_validate(result.reasoning),
        supporting_evidence=result.supporting_evidence,
        conflicting_evidence=result.conflicting_evidence,
        risks=result.risks,
        invalidation_conditions=result.invalidation_conditions,
        model_name=result.model_name,
        prompt_version=result.prompt_version,
        ai_available=result.ai_available,
        warnings=result.warnings,
        calculated_at=result.calculated_at,
    )


def _row_to_response(row: AIAnalysis, symbol: str) -> AIAnalysisResponse:
    return AIAnalysisResponse(
        id=row.id,
        symbol=symbol,
        timeframe=row.timeframe,
        recommendation=row.recommendation,
        confidence_score=row.confidence_score,
        confidence_level=row.confidence_level,
        risk_level=row.risk_level,
        entry_price=row.entry_price,
        stop_loss=row.stop_loss,
        take_profit=row.take_profit,
        execution_guidance=row.execution_guidance,
        reasoning=ReasoningResponse.model_validate(row.reasoning),
        supporting_evidence=row.supporting_evidence,
        conflicting_evidence=row.conflicting_evidence,
        risks=row.risks,
        invalidation_conditions=row.invalidation_conditions,
        model_name=row.model_name,
        prompt_version=row.prompt_version,
        ai_available=row.ai_available,
        warnings=row.warnings,
        calculated_at=row.created_at,
    )


@router.post("/analysis/ai/{symbol}", response_model=AIAnalysisResponse)
async def generate_ai_analysis(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    current_user: Annotated[User, Depends(get_current_user)],
    engine: Annotated[AIOrchestratorEngine, Depends(get_ai_orchestrator_engine)],
) -> AIAnalysisResponse:
    result = engine.generate(asset, timeframe)
    return _result_to_response(result)


@router.get("/analysis/ai/{analysis_id}", response_model=AIAnalysisResponse)
async def get_ai_analysis(
    analysis_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    ai_analysis_repository: Annotated[AIAnalysisRepository, Depends(get_ai_analysis_repository)],
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
) -> AIAnalysisResponse:
    row = ai_analysis_repository.get_by_id(analysis_id)
    if row is None:
        raise ResourceNotFoundException(f"Unknown AI analysis id: {analysis_id}")

    asset = asset_repository.get_by_id(row.asset_id)
    symbol = asset.symbol if asset is not None else "UNKNOWN"
    return _row_to_response(row, symbol)


@router.get("/analysis/history", response_model=AIAnalysisListResponse)
async def get_ai_analysis_history(
    current_user: Annotated[User, Depends(get_current_user)],
    ai_analysis_repository: Annotated[AIAnalysisRepository, Depends(get_ai_analysis_repository)],
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
    symbol: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AIAnalysisListResponse:
    asset_id = None
    if symbol is not None:
        asset = asset_repository.get_by_symbol(symbol.upper())
        if asset is None:
            raise ResourceNotFoundException(f"Unknown asset symbol: {symbol.upper()}")
        asset_id = asset.id

    offset = (page - 1) * limit
    rows = ai_analysis_repository.find_paginated(asset_id=asset_id, offset=offset, limit=limit)
    total = ai_analysis_repository.count_filtered(asset_id=asset_id)

    items = []
    for row in rows:
        asset = asset_repository.get_by_id(row.asset_id)
        items.append(_row_to_response(row, asset.symbol if asset is not None else "UNKNOWN"))

    return AIAnalysisListResponse(items=items, page=page, limit=limit, total=total)
