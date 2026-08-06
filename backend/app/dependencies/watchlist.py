from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.dependencies.market_data import get_asset_repository
from app.repositories.asset_repository import AssetRepository
from app.repositories.watchlist_repository import WatchlistRepository
from app.services.watchlist_service import WatchlistService


def get_watchlist_repository(db: Annotated[Session, Depends(get_db)]) -> WatchlistRepository:
    return WatchlistRepository(db)


def get_watchlist_service(
    watchlist_repository: Annotated[WatchlistRepository, Depends(get_watchlist_repository)],
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
) -> WatchlistService:
    return WatchlistService(
        watchlist_repository=watchlist_repository, asset_repository=asset_repository
    )
