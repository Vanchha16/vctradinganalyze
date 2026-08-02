from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.routes.market_data import get_asset_or_404
from app.dependencies import get_current_user
from app.dependencies.market_data import get_asset_repository
from app.dependencies.signal import (
    get_signal_bookmark_repository,
    get_signal_engine,
    get_signal_repository,
)
from app.exceptions import ConflictException, ResourceNotFoundException
from app.models.asset import Asset
from app.models.enums import SignalStatus, Timeframe
from app.models.signal import Signal
from app.models.signal_bookmark import SignalBookmark
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.repositories.signal_bookmark_repository import SignalBookmarkRepository
from app.repositories.signal_repository import SignalRepository
from app.schemas.signal import (
    BookmarkRequest,
    BookmarkResponse,
    SignalGenerationResponse,
    SignalListResponse,
    SignalResponse,
)
from app.services.signal import status_resolver
from app.services.signal_engine import SignalEngine, SignalGenerationResult

router = APIRouter(tags=["signals"])

_BookmarkRepo = Annotated[SignalBookmarkRepository, Depends(get_signal_bookmark_repository)]


def _signal_to_response(signal: Signal, symbol: str) -> SignalResponse:
    effective_status = status_resolver.effective_status(
        signal.status, signal.created_at, datetime.now(UTC)
    )
    return SignalResponse(
        id=signal.id,
        analysis_id=signal.analysis_id,
        symbol=symbol,
        timeframe=signal.timeframe,
        signal_type=signal.signal_type,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        risk_reward=signal.risk_reward,
        confidence=signal.confidence,
        status=effective_status,
        triggered_at=signal.triggered_at,
        closed_at=signal.closed_at,
        profit_loss=signal.profit_loss,
        created_at=signal.created_at,
    )


def _generation_result_to_response(
    result: SignalGenerationResult, symbol: str
) -> SignalGenerationResponse:
    return SignalGenerationResponse(
        analysis_id=result.analysis_id,
        symbol=symbol,
        timeframe=result.timeframe,
        recommendation=result.recommendation,
        signal=_signal_to_response(result.signal, symbol) if result.signal is not None else None,
    )


@router.post("/signals/generate/{symbol}", response_model=SignalGenerationResponse)
async def generate_signal(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    current_user: Annotated[User, Depends(get_current_user)],
    engine: Annotated[SignalEngine, Depends(get_signal_engine)],
) -> SignalGenerationResponse:
    """docs/51 §6 (ADR-089) - on-demand generation, mirrors
    `POST /analysis/ai/{symbol}`'s pattern. `signal` is `null` when the
    underlying recommendation is WAIT (ADR-086)."""
    result = engine.generate(asset, timeframe)
    return _generation_result_to_response(result, asset.symbol)


@router.get("/signals", response_model=SignalListResponse)
async def list_signals(
    current_user: Annotated[User, Depends(get_current_user)],
    signal_repository: Annotated[SignalRepository, Depends(get_signal_repository)],
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
    symbol: Annotated[str | None, Query()] = None,
    status: Annotated[SignalStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SignalListResponse:
    asset_id = None
    if symbol is not None:
        asset = asset_repository.get_by_symbol(symbol.upper())
        if asset is None:
            raise ResourceNotFoundException(f"Unknown asset symbol: {symbol.upper()}")
        asset_id = asset.id

    offset = (page - 1) * limit
    rows = signal_repository.find_paginated(
        asset_id=asset_id, status=status, offset=offset, limit=limit
    )
    total = signal_repository.count_filtered(asset_id=asset_id, status=status)

    items = []
    for row in rows:
        asset = asset_repository.get_by_id(row.asset_id)
        items.append(_signal_to_response(row, asset.symbol if asset is not None else "UNKNOWN"))

    return SignalListResponse(items=items, page=page, limit=limit, total=total)


@router.get("/signals/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    signal_repository: Annotated[SignalRepository, Depends(get_signal_repository)],
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
) -> SignalResponse:
    row = signal_repository.get_by_id(signal_id)
    if row is None:
        raise ResourceNotFoundException(f"Unknown signal id: {signal_id}")

    asset = asset_repository.get_by_id(row.asset_id)
    symbol = asset.symbol if asset is not None else "UNKNOWN"
    return _signal_to_response(row, symbol)


@router.post("/signals/bookmark", response_model=BookmarkResponse)
async def bookmark_signal(
    body: BookmarkRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    signal_repository: Annotated[SignalRepository, Depends(get_signal_repository)],
    bookmark_repository: _BookmarkRepo,
) -> BookmarkResponse:
    signal = signal_repository.get_by_id(body.signal_id)
    if signal is None:
        raise ResourceNotFoundException(f"Unknown signal id: {body.signal_id}")

    existing = bookmark_repository.get_by_user_and_signal(current_user.id, body.signal_id)
    if existing is not None:
        raise ConflictException("Signal is already bookmarked.")

    bookmark = SignalBookmark(user_id=current_user.id, signal_id=body.signal_id)
    bookmark_repository.create(bookmark)
    bookmark_repository.commit()
    return BookmarkResponse.model_validate(bookmark)


@router.delete("/signals/bookmark/{bookmark_id}", status_code=204)
async def remove_signal_bookmark(
    bookmark_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    bookmark_repository: _BookmarkRepo,
) -> None:
    bookmark = bookmark_repository.get_by_id(bookmark_id)
    if bookmark is None or bookmark.user_id != current_user.id:
        raise ResourceNotFoundException(f"Unknown bookmark id: {bookmark_id}")

    bookmark_repository.delete(bookmark)
    bookmark_repository.commit()
