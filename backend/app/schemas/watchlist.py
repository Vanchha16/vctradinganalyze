import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.market_data import AssetResponse


class WatchlistCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WatchlistRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WatchlistAddAssetRequest(BaseModel):
    asset_id: uuid.UUID


class WatchlistSummaryResponse(BaseModel):
    """docs/58 §2.3 `GET /watchlists` - a watchlist plus its item count,
    no resolved asset rows (that's `GET /watchlists/{id}` only)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    item_count: int
    created_at: datetime


class WatchlistListResponse(BaseModel):
    items: list[WatchlistSummaryResponse]


class WatchlistDetailResponse(BaseModel):
    """`GET /watchlists/{id}` - an inferred addition beyond docs/04's
    literal endpoint list (ADR-128), needed for the 7D-B detail view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
    assets: list[AssetResponse]
