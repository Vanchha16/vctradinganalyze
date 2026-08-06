"""`GET /admin/{signals,system,analytics}`, `POST /admin/{news,maintenance}`
(docs/58 §3.2, Phase 7D-C, ADR-130). Mirrors `admin_users.py`/
`admin_logs.py`'s flat-module structure and `GET /admin/users`'
pagination convention exactly.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.dependencies.admin import get_admin_system_service
from app.dependencies.market_data import get_asset_repository
from app.dependencies.rbac import require_admin
from app.exceptions import ResourceNotFoundException
from app.models.enums import SignalStatus
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.schemas.admin_system import (
    AdminAnalyticsResponse,
    AdminSystemStatusResponse,
    CalendarRefreshResponse,
    MaintenanceActionRequest,
    MaintenanceActionResponse,
    NewsRefreshResponse,
)
from app.schemas.signal import SignalListResponse, SignalResponse
from app.services.admin_system_service import AdminSystemService
from app.services.signal import status_resolver

router = APIRouter(prefix="/admin", tags=["admin"])

_Service = Annotated[AdminSystemService, Depends(get_admin_system_service)]


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/signals", response_model=SignalListResponse)
async def list_admin_signals(
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
    symbol: Annotated[str | None, Query()] = None,
    status: Annotated[SignalStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SignalListResponse:
    """docs/58 §3.2's "admin view (all users, not just caller's)" - `Signal`
    has no `user_id` at all (ADR-130); this returns the same globally-
    scoped rows `GET /signals` already does, under the admin surface."""
    asset_id = None
    if symbol is not None:
        asset = asset_repository.get_by_symbol(symbol.upper())
        if asset is None:
            raise ResourceNotFoundException(f"Unknown asset symbol: {symbol.upper()}")
        asset_id = asset.id

    items, total = service.list_signals(asset_id=asset_id, status=status, page=page, limit=limit)

    now = datetime.now(UTC)
    response_items = []
    for row in items:
        asset = asset_repository.get_by_id(row.asset_id)
        response_items.append(
            SignalResponse(
                id=row.id,
                analysis_id=row.analysis_id,
                symbol=asset.symbol if asset is not None else "UNKNOWN",
                timeframe=row.timeframe,
                signal_type=row.signal_type,
                entry_price=row.entry_price,
                stop_loss=row.stop_loss,
                take_profit=row.take_profit,
                risk_reward=row.risk_reward,
                confidence=row.confidence,
                status=status_resolver.effective_status(row.status, row.created_at, now),
                triggered_at=row.triggered_at,
                closed_at=row.closed_at,
                profit_loss=row.profit_loss,
                created_at=row.created_at,
            )
        )
    return SignalListResponse(items=response_items, page=page, limit=limit, total=total)


@router.get("/system", response_model=AdminSystemStatusResponse)
async def get_admin_system_status(
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AdminSystemStatusResponse:
    return service.get_system_status()


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_admin_analytics(
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> AdminAnalyticsResponse:
    return service.get_analytics()


@router.post("/news", response_model=NewsRefreshResponse)
async def refresh_news(
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> NewsRefreshResponse:
    """docs/58 §3.2 - calls the same `NewsIngestionPipeline` the Celery
    beat schedule uses, just admin-invoked. Runs inline/blocking per the
    approved spec - see ADR-130 for the synchronous-ingestion tradeoff."""
    articles_ingested = service.refresh_news(actor, ip_address=_client_ip(request))
    return NewsRefreshResponse(articles_ingested=articles_ingested)


@router.post("/maintenance", response_model=MaintenanceActionResponse)
async def run_maintenance(
    body: MaintenanceActionRequest,
    request: Request,
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
) -> MaintenanceActionResponse:
    """Scoped to exactly `refresh_news`/`refresh_calendar` (ADR-117) - any
    other action is already rejected by `MaintenanceActionRequest`'s
    `Literal` before this handler runs. Shares `AdminSystemService.
    refresh_news`/`refresh_calendar` with `POST /admin/news` (docs/58 §3.2's
    deliberate overlap, ADR-130) - not duplicated here."""
    if body.action == "refresh_news":
        articles_ingested = service.refresh_news(actor, ip_address=_client_ip(request))
        return MaintenanceActionResponse(
            action="refresh_news", news=NewsRefreshResponse(articles_ingested=articles_ingested)
        )

    created, updated = service.refresh_calendar(actor, ip_address=_client_ip(request))
    return MaintenanceActionResponse(
        action="refresh_calendar",
        calendar=CalendarRefreshResponse(events_created=created, events_updated=updated),
    )
