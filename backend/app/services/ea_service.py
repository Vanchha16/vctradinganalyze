"""MT5 Expert Advisor access (ADR-161).

The EA runs in the operator's own MetaTrader 5 terminal and places trades
there. What the platform does for it is deliberately small: issue a
token, authenticate the EA by that token, and list the signals that are
currently open. It never receives broker credentials and has no code path
that places, modifies or cancels an order - execution happens entirely on
the operator's machine.
"""

import secrets
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog

from app.config import settings
from app.core.security import hash_token
from app.exceptions import ConflictException, InvalidEaTokenException, ResourceNotFoundException
from app.models.audit_log import AuditLog
from app.models.ea_token import EaToken
from app.models.enums import SignalStatus, UserRole
from app.models.signal import Signal
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.ea_token_repository import EaTokenRepository
from app.repositories.signal_repository import SignalRepository
from app.services.signal import status_resolver
from app.utils.time import as_aware_utc

logger = structlog.get_logger(__name__)

#: Recognisable in a pasted config or a leaked log line, so it can be
#: identified and revoked. Also lets `authenticate` reject a stray JWT or
#: API key without a database lookup.
TOKEN_PREFIX = "vcea_"

#: Who may hold a working token. Super admin only while execution is
#: single-operator (XAUUSD first). Checked on every feed request, not just
#: at creation, so demoting a user disables their EAs immediately.
ALLOWED_ROLES = frozenset({UserRole.SUPER_ADMIN})

#: Enough for a home PC, a VPS and a spare; a higher count is more likely
#: forgotten terminals than real need.
MAX_TOKENS_PER_USER = 5

#: An EA polls every few seconds. Writing `last_used_at` on every poll
#: would be a commit per request for a value read at minute resolution.
_LAST_USED_RESOLUTION = timedelta(minutes=1)

_FEED_STATUSES = frozenset({SignalStatus.ACTIVE, SignalStatus.TRIGGERED})


@dataclass(frozen=True, slots=True)
class FeedSignal:
    signal: Signal
    #: Read-time status (ADR-088/137), not the stored column.
    status: SignalStatus
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class EaPrincipal:
    """An authenticated EA: the user it acts for, and the token - i.e. the
    terminal - it authenticated with. Event reports need both (ADR-162)."""

    user: User
    token: EaToken


class EaService:
    def __init__(
        self,
        token_repository: EaTokenRepository,
        signal_repository: SignalRepository,
        asset_repository: AssetRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._token_repository = token_repository
        self._signal_repository = signal_repository
        self._asset_repository = asset_repository
        self._audit_log_repository = audit_log_repository

    def list_tokens(self, user: User) -> Sequence[EaToken]:
        return self._token_repository.list_for_user(user.id)

    def create_token(self, user: User, name: str) -> tuple[EaToken, str]:
        """Returns the row and the raw token. The raw token is not stored
        and cannot be recovered - losing it means revoking and creating
        another."""
        if self._token_repository.count_for_user(user.id) >= MAX_TOKENS_PER_USER:
            raise ConflictException(
                f"You already have {MAX_TOKENS_PER_USER} EA tokens. Revoke one first."
            )

        raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
        token = EaToken(
            user_id=user.id, name=name.strip(), token_hash=hash_token(raw), hint=raw[-4:]
        )
        self._token_repository.create(token)
        self._audit(
            user.id,
            action="ea_token_created",
            context={"token_id": str(token.id), "name": token.name, "hint": token.hint},
        )
        self._commit()
        logger.info("ea.token_created", user_id=str(user.id), token_id=str(token.id))
        return token, raw

    def revoke_token(self, user: User, token_id: uuid.UUID) -> None:
        """Deletes the row, so the next poll from that EA is a 401.

        404 rather than 403 for another user's token, so the response does
        not confirm that the id exists."""
        token = self._token_repository.get_by_id(token_id)
        if token is None or token.user_id != user.id:
            raise ResourceNotFoundException(f"Unknown EA token id: {token_id}")

        self._token_repository.delete(token)
        self._audit(
            user.id,
            action="ea_token_revoked",
            context={"token_id": str(token_id), "name": token.name, "hint": token.hint},
        )
        self._commit()
        logger.info("ea.token_revoked", user_id=str(user.id), token_id=str(token_id))

    def authenticate(self, raw_token: str | None, now: datetime) -> EaPrincipal:
        """Every failure is the same 401, whether the token is malformed,
        unknown, or belongs to a user who is inactive or no longer allowed
        - a caller probing tokens learns nothing from the difference."""
        if not raw_token or not raw_token.startswith(TOKEN_PREFIX):
            raise InvalidEaTokenException()

        token = self._token_repository.get_by_hash(hash_token(raw_token))
        if token is None:
            raise InvalidEaTokenException()

        user = self._token_repository.session.get(User, token.user_id)
        if (
            user is None
            or not user.is_active
            or user.deleted_at is not None
            or user.role not in ALLOWED_ROLES
        ):
            raise InvalidEaTokenException()

        if (
            token.last_used_at is None
            or now - as_aware_utc(token.last_used_at) >= _LAST_USED_RESOLUTION
        ):
            token.last_used_at = now
            self._commit()
        return EaPrincipal(user=user, token=token)

    def open_signals(self, symbol: str, now: datetime) -> list[FeedSignal]:
        """Signals an EA may still act on, newest first.

        `active` - no fill yet; the EA may place an order.
        `triggered` - price reached entry; the EA keeps an order it already
        has but must not open a new one for it.

        Anything else (expired, closed, successful, stopped out) is left
        out, and a signal dropping out of this list is the EA's cue to
        cancel an unfilled order for it.
        """
        asset = self._asset_repository.get_by_symbol(symbol.upper())
        if asset is None:
            raise ResourceNotFoundException(f"Unknown asset symbol: {symbol.upper()}")

        # A triggered signal stays open up to `signal_triggered_ttl_hours`
        # after it triggered, which can itself be up to `signal_ttl_hours`
        # after creation - so both windows bound how far back to look.
        lookback = timedelta(hours=settings.signal_ttl_hours + settings.signal_triggered_ttl_hours)
        rows = self._signal_repository.find_open_for_asset(asset.id, created_since=now - lookback)

        feed: list[FeedSignal] = []
        for row in rows:
            status = status_resolver.effective_status(
                row.status, row.created_at, now, triggered_at=row.triggered_at
            )
            if status not in _FEED_STATUSES:
                continue
            expires_at = as_aware_utc(row.created_at) + timedelta(hours=settings.signal_ttl_hours)
            feed.append(FeedSignal(signal=row, status=status, expires_at=expires_at))
        return feed

    def _audit(self, actor_id: uuid.UUID, *, action: str, context: dict[str, Any]) -> None:
        self._audit_log_repository.create(
            AuditLog(
                user_id=actor_id,
                action=action,
                resource="ea_token",
                resource_id=None,
                context=context,
            )
        )

    def _commit(self) -> None:
        self._token_repository.session.commit()


__all__ = [
    "ALLOWED_ROLES",
    "MAX_TOKENS_PER_USER",
    "TOKEN_PREFIX",
    "EaPrincipal",
    "EaService",
    "FeedSignal",
]
