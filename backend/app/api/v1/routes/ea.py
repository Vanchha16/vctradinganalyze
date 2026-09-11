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
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.config import settings
from app.dependencies.ea import get_ea_service, get_ea_user
from app.dependencies.rate_limit import rate_limit_public
from app.dependencies.rbac import require_super_admin
from app.models.user import User
from app.schemas.ea import (
    EaSignalFeedResponse,
    EaSignalResponse,
    EaTokenCreatedResponse,
    EaTokenCreateRequest,
    EaTokenListResponse,
    EaTokenResponse,
)
from app.services.ea_service import EaService, FeedSignal
from app.utils.time import as_aware_utc

router = APIRouter(prefix="/ea", tags=["expert-advisor"])

_Service = Annotated[EaService, Depends(get_ea_service)]

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
    return EaTokenListResponse(
        items=[EaTokenResponse.model_validate(t) for t in service.list_tokens(actor)]
    )


@router.post("/tokens", response_model=EaTokenCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_ea_token(
    payload: EaTokenCreateRequest,
    actor: Annotated[User, Depends(require_super_admin)],
    service: _Service,
) -> EaTokenCreatedResponse:
    """The response is the only place the raw token ever appears."""
    token, raw = service.create_token(actor, payload.name)
    return EaTokenCreatedResponse(
        id=token.id,
        name=token.name,
        hint=token.hint,
        created_at=token.created_at,
        last_used_at=token.last_used_at,
        token=raw,
    )


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
    _ea_user: Annotated[User, Depends(get_ea_user)],
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
        signals=[_to_response(item, symbol.upper()) for item in feed],
    )


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
