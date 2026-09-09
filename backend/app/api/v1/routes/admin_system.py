"""`GET /admin/{signals,system,analytics}`, `POST /admin/{news,maintenance}`
(docs/58 §3.2, Phase 7D-C, ADR-130). Mirrors `admin_users.py`/
`admin_logs.py`'s flat-module structure and `GET /admin/users`'
pagination convention exactly.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.client_ip import get_client_ip
from app.dependencies.admin import get_admin_system_service
from app.dependencies.database import get_db
from app.dependencies.market_data import get_asset_repository
from app.dependencies.rbac import require_admin
from app.exceptions import ResourceNotFoundException
from app.models.enums import OrderStatus, SignalStatus
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.repositories.tradingview_alert_repository import TradingViewAlertRepository
from app.schemas.admin_api_usage import AdminApiUsageResponse, ApiUsageRouteResponse
from app.schemas.admin_system import (
    AdminAnalyticsResponse,
    AdminSystemStatusResponse,
    CalendarRefreshResponse,
    MaintenanceActionRequest,
    MaintenanceActionResponse,
    NewsRefreshResponse,
)
from app.schemas.broker_order import BrokerOrderListResponse, BrokerOrderResponse
from app.schemas.signal import SignalListResponse, SignalResponse
from app.schemas.tradingview_alert import (
    TradingViewAlertListResponse,
    TradingViewAlertResponse,
)
from app.services import api_usage_service
from app.services.admin_system_service import AdminSystemService
from app.services.signal import status_resolver

router = APIRouter(prefix="/admin", tags=["admin"])

_Service = Annotated[AdminSystemService, Depends(get_admin_system_service)]


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
                status=status_resolver.effective_status(
                    row.status, row.created_at, now, triggered_at=row.triggered_at
                ),
                triggered_at=row.triggered_at,
                closed_at=row.closed_at,
                profit_loss=row.profit_loss,
                created_at=row.created_at,
            )
        )
    return SignalListResponse(items=response_items, page=page, limit=limit, total=total)


@router.get("/orders", response_model=BrokerOrderListResponse)
async def list_admin_broker_orders(
    actor: Annotated[User, Depends(require_admin)],
    service: _Service,
    status: Annotated[OrderStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BrokerOrderListResponse:
    """EA Bot spec §3F - every real order this bot has ever placed,
    view-only (no manual close/modify from the dashboard this phase)."""
    items, total = service.list_broker_orders(status=status, page=page, limit=limit)
    response_items = [BrokerOrderResponse.model_validate(row) for row in items]
    return BrokerOrderListResponse(items=response_items, page=page, limit=limit, total=total)


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
    articles_ingested = service.refresh_news(actor, ip_address=get_client_ip(request))
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
        articles_ingested = service.refresh_news(actor, ip_address=get_client_ip(request))
        return MaintenanceActionResponse(
            action="refresh_news", news=NewsRefreshResponse(articles_ingested=articles_ingested)
        )

    created, updated = service.refresh_calendar(actor, ip_address=get_client_ip(request))
    return MaintenanceActionResponse(
        action="refresh_calendar",
        calendar=CalendarRefreshResponse(events_created=created, events_updated=updated),
    )


@router.get("/api-usage", response_model=AdminApiUsageResponse)
async def get_admin_api_usage(
    actor: Annotated[User, Depends(require_admin)],
) -> AdminApiUsageResponse:
    """ADR-144: a human-readable fold of the Prometheus request metrics
    ADR-136 already collects, for the Admin API Usage page (which until
    now was a placeholder claiming - wrongly, since Phase 9D - that no
    request-metrics infrastructure existed).

    `require_admin`, not `require_metrics_token`: this is an operator
    page behind the normal admin session, whereas `GET /metrics` is the
    machine surface for a scraper with its own credential. Both read the
    same in-process registry, so they can never disagree.

    Takes no `AdminSystemService` - there is nothing to inject. The data
    lives in the `prometheus_client` registry of this very process, not
    in the database.
    """
    snapshot = api_usage_service.build_snapshot()
    return AdminApiUsageResponse(
        total_requests=snapshot.total_requests,
        total_errors=snapshot.total_errors,
        error_rate=snapshot.error_rate,
        avg_latency_ms=snapshot.avg_latency_ms,
        p95_latency_ms=snapshot.p95_latency_ms,
        route_count=snapshot.route_count,
        status_2xx=snapshot.status_2xx,
        status_3xx=snapshot.status_3xx,
        status_4xx=snapshot.status_4xx,
        status_5xx=snapshot.status_5xx,
        routes=[
            ApiUsageRouteResponse(
                method=route.method,
                route=route.route,
                requests=route.requests,
                errors=route.errors,
                error_rate=route.error_rate,
                avg_latency_ms=route.avg_latency_ms,
                p95_latency_ms=route.p95_latency_ms,
            )
            for route in snapshot.routes
        ],
    )


@router.get("/tradingview-alerts", response_model=TradingViewAlertListResponse)
async def list_tradingview_alerts(
    actor: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    symbol: Annotated[str | None, Query()] = None,
    direction: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TradingViewAlertListResponse:
    """ADR-146: read side for inbound TradingView webhook alerts, same
    pagination envelope as `GET /admin/users`/`GET /admin/logs`.

    Read-only by design - nothing in this project mutates an alert after
    the webhook stores it, except the delivery task stamping
    `delivered_at`. There is deliberately no endpoint to replay an alert
    into the signal pipeline: alerts and AI signals are separate all the
    way down, and a replay route would quietly join them.
    """
    repository = TradingViewAlertRepository(session)
    offset = (page - 1) * limit
    alerts = repository.list_filtered(
        symbol=symbol, direction=direction, offset=offset, limit=limit
    )
    total = repository.count_filtered(symbol=symbol, direction=direction)
    return TradingViewAlertListResponse(
        items=[
            TradingViewAlertResponse(
                id=str(alert.id),
                symbol=alert.symbol,
                exchange=alert.exchange,
                timeframe=alert.timeframe,
                direction=alert.direction,
                score=alert.score,
                entry_price=alert.entry_price,
                alert_time=alert.alert_time,
                source=alert.source,
                delivered_at=alert.delivered_at,
                created_at=alert.created_at,
            )
            for alert in alerts
        ],
        page=page,
        limit=limit,
        total=total,
    )
