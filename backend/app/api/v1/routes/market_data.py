from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import (
    get_asset_repository,
    get_indicator_result_repository,
    get_price_candle_repository,
)
from app.exceptions import ResourceNotFoundException, ValidationException
from app.indicators import registry
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.price_candle import PriceCandle
from app.repositories.asset_repository import AssetRepository
from app.repositories.indicator_result_repository import IndicatorResultRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.schemas.market_data import (
    AssetListResponse,
    AssetResponse,
    CandleListResponse,
    CandleResponse,
    IndicatorListResponse,
    IndicatorResultResponse,
)

router = APIRouter(tags=["market-data"])

#: Computed once at import time - `app.indicators`'s registration happens
#: on import, so every registered indicator is already present here
#: (docs/39, refinement: validate against the registry, not any string).
_VALID_INDICATOR_NAMES = frozenset(spec.name for spec in registry.list_all())

_MAX_TIME_SERIES_LIMIT = 1000


def get_asset_or_404(
    symbol: str,
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
) -> Asset:
    """Shared 404 lookup, normalizing casing (`eurusd` == `EURUSD`) -
    reused by every route keyed on a symbol path parameter."""
    asset = asset_repository.get_by_symbol(symbol.upper())
    if asset is None:
        raise ResourceNotFoundException(f"Unknown asset symbol: {symbol.upper()}")
    return asset


@router.get("/assets", response_model=AssetListResponse)
async def list_assets(
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
    market_type: Annotated[MarketType | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AssetListResponse:
    offset = (page - 1) * limit
    items = asset_repository.list_filtered(
        market_type=market_type, is_active=is_active, offset=offset, limit=limit
    )
    total = asset_repository.count_filtered(market_type=market_type, is_active=is_active)
    return AssetListResponse(
        items=[AssetResponse.model_validate(a) for a in items], page=page, limit=limit, total=total
    )


@router.get("/assets/{symbol}", response_model=AssetResponse)
async def get_asset(asset: Annotated[Asset, Depends(get_asset_or_404)]) -> Asset:
    return asset


@router.get("/market/{symbol}/latest", response_model=CandleResponse)
async def get_latest_candle(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    price_candle_repository: Annotated[PriceCandleRepository, Depends(get_price_candle_repository)],
) -> PriceCandle:
    candle = price_candle_repository.get_latest(asset.id, timeframe)
    if candle is None:
        raise ResourceNotFoundException(f"No {timeframe.value} candles yet for {asset.symbol}")
    return candle


@router.get("/market/{symbol}/candles", response_model=CandleListResponse)
async def get_candles(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    price_candle_repository: Annotated[PriceCandleRepository, Depends(get_price_candle_repository)],
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=_MAX_TIME_SERIES_LIMIT)] = 100,
) -> CandleListResponse:
    if from_ is not None:
        candles = price_candle_repository.list_range(
            asset.id, timeframe, start=from_, end=to or datetime.now(UTC), limit=limit
        )
    else:
        candles = price_candle_repository.list_recent(asset.id, timeframe, limit=limit)

    return CandleListResponse(
        symbol=asset.symbol,
        timeframe=timeframe,
        items=[CandleResponse.model_validate(c) for c in candles],
    )


@router.get("/market/{symbol}/indicators", response_model=IndicatorListResponse)
async def get_indicators(
    asset: Annotated[Asset, Depends(get_asset_or_404)],
    timeframe: Timeframe,
    indicator_result_repository: Annotated[
        IndicatorResultRepository, Depends(get_indicator_result_repository)
    ],
    indicator: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=_MAX_TIME_SERIES_LIMIT)] = 100,
) -> IndicatorListResponse:
    if indicator is not None and indicator not in _VALID_INDICATOR_NAMES:
        raise ValidationException(
            f"Unknown indicator {indicator!r}. Valid indicators: {sorted(_VALID_INDICATOR_NAMES)}"
        )

    results = indicator_result_repository.list_for_asset_timeframe(
        asset.id, timeframe, indicator=indicator, limit=limit
    )
    return IndicatorListResponse(
        symbol=asset.symbol,
        timeframe=timeframe,
        items=[IndicatorResultResponse.model_validate(r) for r in results],
    )
