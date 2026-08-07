"""Admin symbol/asset management (Phase 9F, ADR-138).

Mirrors `admin_users.py`'s shape exactly - same pagination convention
(param names, response envelope), same `require_admin` gate. `activate`/
`deactivate` are separate `POST` actions (not a single `PATCH .../status`
like Users) to keep each one-line, self-describing in an audit log/API
log without a body to inspect.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.core.client_ip import get_client_ip
from app.dependencies.admin import get_admin_asset_service
from app.dependencies.rbac import require_admin
from app.models.enums import MarketType
from app.models.user import User
from app.schemas.admin import AdminAssetCreateRequest, AdminAssetUpdateRequest
from app.schemas.market_data import AssetListResponse, AssetResponse
from app.services.admin_asset_service import AdminAssetService

router = APIRouter(prefix="/admin/assets", tags=["admin"])

_Service = Annotated[AdminAssetService, Depends(get_admin_asset_service)]


@router.get("", response_model=AssetListResponse)
async def list_assets(
    _actor: Annotated[User, Depends(require_admin)],
    service: _Service,
    search: Annotated[str | None, Query()] = None,
    market_type: Annotated[MarketType | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AssetListResponse:
    items, total = service.list_assets(
        search=search, market_type=market_type, is_active=is_active, page=page, limit=limit
    )
    return AssetListResponse(
        items=[AssetResponse.model_validate(a) for a in items], page=page, limit=limit, total=total
    )


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset(
    payload: AdminAssetCreateRequest,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AssetResponse:
    asset = service.create_asset(
        actor,
        symbol=payload.symbol,
        name=payload.name,
        market_type=payload.market_type,
        exchange=payload.exchange,
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        ip_address=get_client_ip(request),
    )
    return AssetResponse.model_validate(asset)


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID,
    payload: AdminAssetUpdateRequest,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AssetResponse:
    asset = service.update_asset(
        actor,
        asset_id,
        symbol=payload.symbol,
        name=payload.name,
        market_type=payload.market_type,
        exchange=payload.exchange,
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        ip_address=get_client_ip(request),
    )
    return AssetResponse.model_validate(asset)


@router.post("/{asset_id}/activate", response_model=AssetResponse)
async def activate_asset(
    asset_id: UUID,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AssetResponse:
    asset = service.activate(actor, asset_id, ip_address=get_client_ip(request))
    return AssetResponse.model_validate(asset)


@router.post("/{asset_id}/deactivate", response_model=AssetResponse)
async def deactivate_asset(
    asset_id: UUID,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AssetResponse:
    asset = service.deactivate(actor, asset_id, ip_address=get_client_ip(request))
    return AssetResponse.model_validate(asset)
