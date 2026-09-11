"""MT5 Expert Advisor routes (ADR-161).

Two audiences:

- **The operator, in the browser** (`/ea/tokens`) - session-authenticated,
  super admin only. Creates, lists and revokes EA tokens.
- **The EA, in MetaTrader 5** (`/ea/signals`) - authenticated only by the
  `X-EA-Token` header. Read-only: this is the entire surface an EA token
  can reach.

Nothing here places an order. Execution happens inside the operator's own
MT5 terminal; the platform only publishes what the signals are.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.config import settings
from app.dependencies.ea import (
    get_ea_event_service,
    get_ea_principal,
    get_ea_service,
)
from app.dependencies.rate_limit import rate_limit_public
from app.dependencies.rbac import require_super_admin
from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import SignalType
from app.models.user import User
from app.schemas.ea import (
    EaEventBatchRequest,
    EaEventBatchResponse,
    EaEventListResponse,
    EaEventRejection,
    EaEventResponse,
    EaEventType,
    EaSettings,
    EaSettingsResponse,
    EaSignalFeedResponse,
    EaSignalResponse,
    EaTerminalState,
    EaTokenCreatedResponse,
    EaTokenCreateRequest,
    EaTokenListResponse,
    EaTokenResponse,
)
from app.services.ea_event_service import EaEventService
from app.services.ea_service import EaPrincipal, EaService, FeedSignal
from app.utils.time import as_aware_utc

router = APIRouter(prefix="/ea", tags=["expert-advisor"])

_Service = Annotated[EaService, Depends(get_ea_service)]
_EventService = Annotated[EaEventService, Depends(get_ea_event_service)]

#: Same reasoning as `_feed_rate_limit` - resolved before the token check.
_events_rate_limit = Depends(
    rate_limit_public(
        "ea_events", settings.ea_events_rate_limit, settings.public_rate_limit_window_seconds
    )
)

#: Per-IP, and resolved before the token is checked (decorator
#: dependencies run first), so guessing tokens is rate limited too.
_feed_rate_limit = Depends(
    rate_limit_public(
        "ea_feed", settings.ea_feed_rate_limit, settings.public_rate_limit_window_seconds
    )
)


@router.get("/tokens", response_model=EaTokenListResponse)
async def list_ea_tokens(
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> EaTokenListResponse:
    return EaTokenListResponse(items=[_token_response(t) for t in service.list_tokens(actor)])


@router.post("/tokens", response_model=EaTokenCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_ea_token(
    payload: EaTokenCreateRequest,
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> EaTokenCreatedResponse:
    """The response is the only place the raw token ever appears."""
    token, raw = service.create_token(actor, payload.name)
    return EaTokenCreatedResponse(**_token_response(token).model_dump(), token=raw)


@router.put("/tokens/{token_id}/settings", response_model=EaTokenResponse)
async def update_ea_settings(
    token_id: UUID,
    payload: EaSettings,
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> EaTokenResponse:
    """ADR-163 - reaches the terminal on its next feed poll. The response's
    `terminal.applied_settings_version` catches up once it has."""
    token = service.update_settings(actor, token_id, payload, datetime.now(UTC))
    return _token_response(token)


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_ea_token(
    token_id: UUID,
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> None:
    service.revoke_token(actor, token_id)


@router.get(
    "/signals", response_model=EaSignalFeedResponse, dependencies=[_feed_rate_limit]
)
async def ea_signal_feed(
    principal: Annotated[EaPrincipal, Depends(get_ea_principal)],
    service: _Service,
    symbol: Annotated[str, Query(min_length=1, max_length=32)],
) -> EaSignalFeedResponse:
    """Currently-open signals for one platform symbol (e.g. `XAUUSD`, not
    the broker's `XAUUSDc` - mapping to the broker symbol is the EA's job,
    since it differs per broker and account type)."""
    now = datetime.now(UTC)
    feed = service.open_signals(symbol, now)
    return EaSignalFeedResponse(
        server_time=int(now.timestamp()),
        symbol=symbol.upper(),
        settings=_settings_response(principal.token),
        signals=[_to_response(item, symbol.upper()) for item in feed],
    )


def _settings_response(token: EaToken) -> EaSettingsResponse:
    return EaSettingsResponse(
        paused=token.paused,
        dry_run=token.dry_run,
        lot_size=float(token.lot_size),
        max_open_trades=token.max_open_trades,
        max_slippage_points=token.max_slippage_points,
        version=token.settings_version,
        updated_at=(
            as_aware_utc(token.settings_updated_at) if token.settings_updated_at else None
        ),
    )


def _token_response(token: EaToken) -> EaTokenResponse:
    return EaTokenResponse(
        id=token.id,
        name=token.name,
        hint=token.hint,
        created_at=token.created_at,
        last_used_at=token.last_used_at,
        settings=_settings_response(token),
        terminal=EaTerminalState(
            ea_version=token.ea_version,
            max_lot=float(token.ea_max_lot) if token.ea_max_lot is not None else None,
            allow_remote_live=token.ea_allow_remote_live,
            applied_settings_version=token.applied_settings_version,
            dry_run=token.effective_dry_run,
            paused=token.effective_paused,
        ),
    )


@router.post("/events", response_model=EaEventBatchResponse, dependencies=[_events_rate_limit])
async def report_ea_events(
    payload: EaEventBatchRequest,
    principal: Annotated[EaPrincipal, Depends(get_ea_principal)],
    service: _EventService,
) -> EaEventBatchResponse:
    """ADR-162: the EA's report of what it did. Idempotent per
    `event_key` - re-sending a batch is safe and expected after a lost
    response."""
    result = service.ingest(principal, payload.events)
    return EaEventBatchResponse(
        accepted=result.accepted,
        duplicates=result.duplicates,
        rejected=[EaEventRejection(event_key=k, reason=r) for k, r in result.rejected],
    )


@router.get("/events", response_model=EaEventListResponse)
async def list_ea_events(
    actor: Annotated[User, Depends(require_super_admin)],
    service: _EventService,
    signal_id: Annotated[UUID | None, Query()] = None,
    dry_run: Annotated[bool | None, Query()] = None,
    event_type: Annotated[EaEventType | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> EaEventListResponse:
    """The caller's EA activity, newest first. Session only - an EA token
    can report events but cannot read them back."""
    result = service.list_events(
        actor, signal_id=signal_id, dry_run=dry_run, event_type=event_type, page=page, limit=limit
    )
    return EaEventListResponse(
        items=[_event_to_response(e, result.signal_types.get(e.signal_id)) for e in result.items],
        page=page,
        limit=limit,
        total=result.total,
    )


def _event_to_response(event: EaExecutionEvent, signal_type: SignalType | None) -> EaEventResponse:
    return EaEventResponse(
        id=event.id,
        event_type=event.event_type,
        signal_id=event.signal_id,
        signal_type=signal_type,
        dry_run=event.dry_run,
        occurred_at=as_aware_utc(event.occurred_at),
        token_name=event.token_name,
        account_login=event.account_login,
        broker_symbol=event.broker_symbol,
        order_type=event.order_type,
        order_ticket=event.order_ticket,
        position_id=event.position_id,
        volume=_float(event.volume),
        price=_float(event.price),
        stop_loss=_float(event.stop_loss),
        take_profit=_float(event.take_profit),
        profit=_float(event.profit),
        currency=event.currency,
        retcode=event.retcode,
        close_reason=event.close_reason,
        message=event.message,
        created_at=as_aware_utc(event.created_at),
    )


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _to_response(item: FeedSignal, symbol: str) -> EaSignalResponse:
    signal = item.signal
    return EaSignalResponse(
        id=signal.id,
        symbol=symbol,
        timeframe=signal.timeframe,
        signal_type=signal.signal_type,
        entry_price=float(signal.entry_price),
        stop_loss=float(signal.stop_loss),
        take_profit=float(signal.take_profit),
        confidence=signal.confidence,
        status=item.status,
        created_at=int(as_aware_utc(signal.created_at).timestamp()),
        triggered_at=(
            int(as_aware_utc(signal.triggered_at).timestamp())
            if signal.triggered_at is not None
            else None
        ),
        expires_at=int(item.expires_at.timestamp()),
    )


__all__ = ["router"]
