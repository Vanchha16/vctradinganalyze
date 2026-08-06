from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.dependencies.market_data import get_asset_repository
from app.dependencies.watchlist import get_watchlist_service
from app.exceptions import ResourceNotFoundException
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.schemas.market_data import AssetResponse
from app.schemas.watchlist import (
    WatchlistAddAssetRequest,
    WatchlistCreateRequest,
    WatchlistDetailResponse,
    WatchlistListResponse,
    WatchlistRenameRequest,
    WatchlistSummaryResponse,
)
from app.services.watchlist_service import WatchlistService

router = APIRouter(tags=["watchlists"])

_Service = Annotated[WatchlistService, Depends(get_watchlist_service)]
_AssetRepo = Annotated[AssetRepository, Depends(get_asset_repository)]


@router.get("/watchlists", response_model=WatchlistListResponse)
async def list_watchlists(
    current_user: Annotated[User, Depends(get_current_user)],
    service: _Service,
) -> WatchlistListResponse:
    """docs/58 §2.3 - the caller's own watchlists with item counts."""
    rows = service.list_watchlists(current_user.id)
    return WatchlistListResponse(
        items=[
            WatchlistSummaryResponse(
                id=watchlist.id,
                name=watchlist.name,
                item_count=item_count,
                created_at=watchlist.created_at,
            )
            for watchlist, item_count in rows
        ]
    )


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistDetailResponse)
async def get_watchlist(
    watchlist_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: _Service,
    asset_repository: _AssetRepo,
) -> WatchlistDetailResponse:
    """Inferred addition beyond docs/04's literal endpoint list (ADR-128) -
    needed for the 7D-B detail view. Not owning the watchlist is
    indistinguishable from it not existing (`ResourceNotFoundException`)."""
    watchlist, items = service.get_watchlist_detail(current_user.id, watchlist_id)
    assets = [
        AssetResponse.model_validate(asset)
        for asset in (asset_repository.get_by_id(item.asset_id) for item in items)
        if asset is not None
    ]
    return WatchlistDetailResponse(
        id=watchlist.id, name=watchlist.name, created_at=watchlist.created_at, assets=assets
    )


@router.post("/watchlists", response_model=WatchlistSummaryResponse)
async def create_watchlist(
    body: WatchlistCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: _Service,
) -> WatchlistSummaryResponse:
    watchlist = service.create_watchlist(current_user.id, body.name)
    return WatchlistSummaryResponse(
        id=watchlist.id, name=watchlist.name, item_count=0, created_at=watchlist.created_at
    )


@router.put("/watchlists/{watchlist_id}", response_model=WatchlistSummaryResponse)
async def rename_watchlist(
    watchlist_id: UUID,
    body: WatchlistRenameRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: _Service,
) -> WatchlistSummaryResponse:
    watchlist = service.rename_watchlist(current_user.id, watchlist_id, body.name)
    item_count = service.count_items(watchlist.id)
    return WatchlistSummaryResponse(
        id=watchlist.id, name=watchlist.name, item_count=item_count, created_at=watchlist.created_at
    )


@router.delete("/watchlists/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: _Service,
) -> None:
    service.delete_watchlist(current_user.id, watchlist_id)


@router.post("/watchlists/{watchlist_id}/assets", response_model=AssetResponse)
async def add_watchlist_asset(
    watchlist_id: UUID,
    body: WatchlistAddAssetRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: _Service,
    asset_repository: _AssetRepo,
) -> AssetResponse:
    item = service.add_asset(current_user.id, watchlist_id, body.asset_id)
    asset = asset_repository.get_by_id(item.asset_id)
    if asset is None:
        # `service.add_asset` already validated the asset exists moments
        # ago - a concurrent deletion between that check and this lookup
        # is the only way to reach here, same class of race every other
        # route in this project also leaves unhandled (docs never specify
        # asset deletion at all).
        raise ResourceNotFoundException(f"Unknown asset id: {item.asset_id}")
    return AssetResponse.model_validate(asset)


@router.delete("/watchlists/{watchlist_id}/assets/{asset_id}", status_code=204)
async def remove_watchlist_asset(
    watchlist_id: UUID,
    asset_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: _Service,
) -> None:
    service.remove_asset(current_user.id, watchlist_id, asset_id)
