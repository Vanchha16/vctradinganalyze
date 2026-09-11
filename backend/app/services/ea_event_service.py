"""What an MT5 Expert Advisor reports it did (ADR-162).

Reports are the account's record, not the signal's: nothing here reads or
writes `Signal.status`. A signal can be `successful` on the website while
the EA's order never filled, and the reverse - both are true at once, and
this module keeps them apart rather than reconciling one into the other.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy.exc import IntegrityError

from app.exceptions import ConflictException
from app.models.ea_execution_event import EaExecutionEvent
from app.models.enums import SignalType
from app.models.user import User
from app.repositories.ea_execution_event_repository import EaExecutionEventRepository
from app.repositories.signal_repository import SignalRepository
from app.schemas.ea import EaEventIn
from app.services.ea_service import EaPrincipal

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class IngestResult:
    accepted: int
    duplicates: int
    #: (event_key, reason) for events that were well-formed but not stored.
    rejected: list[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class EventPage:
    items: Sequence[EaExecutionEvent]
    total: int
    #: Direction of each signal on the page, looked up in one query.
    signal_types: dict[uuid.UUID, SignalType]


class EaEventService:
    def __init__(
        self,
        event_repository: EaExecutionEventRepository,
        signal_repository: SignalRepository,
    ) -> None:
        self._event_repository = event_repository
        self._signal_repository = signal_repository

    def ingest(self, principal: EaPrincipal, events: Sequence[EaEventIn]) -> IngestResult:
        """Stores what is new, skips what is already stored, and rejects
        per event what cannot be stored - never the whole batch for one
        bad event, since the EA drops a batch once it gets a response and
        a good event must not be lost with it."""
        user_id = principal.user.id
        seen = self._event_repository.existing_keys(user_id, {e.event_key for e in events})
        known_signals = {
            s.id for s in self._signal_repository.list_by_ids({e.signal_id for e in events})
        }

        rows: list[EaExecutionEvent] = []
        duplicates = 0
        rejected: list[tuple[str, str]] = []
        for event in events:
            if event.event_key in seen:
                duplicates += 1
                continue
            if event.signal_id not in known_signals:
                rejected.append((event.event_key, "unknown signal_id"))
                continue
            # Also dedupes within this batch.
            seen.add(event.event_key)
            rows.append(_to_row(principal, event))

        if rows:
            try:
                self._event_repository.add_all(rows)
                self._event_repository.commit()
            except IntegrityError as exc:
                # Only reachable when two sends of the same batch race past
                # `existing_keys`. The EA retries on 409, and the retry
                # finds the keys already stored.
                self._event_repository.rollback()
                raise ConflictException(
                    "These events were reported twice at the same moment. Send the batch again."
                ) from exc

        logger.info(
            "ea.events_ingested",
            user_id=str(user_id),
            token_id=str(principal.token.id),
            accepted=len(rows),
            duplicates=duplicates,
            rejected=len(rejected),
        )
        return IngestResult(accepted=len(rows), duplicates=duplicates, rejected=rejected)

    def list_events(
        self,
        user: User,
        *,
        signal_id: uuid.UUID | None = None,
        dry_run: bool | None = None,
        event_type: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> EventPage:
        """Only the caller's own events - an EA reports for the user whose
        token it holds, and that account is nobody else's business."""
        items = self._event_repository.list_for_user(
            user.id,
            signal_id=signal_id,
            dry_run=dry_run,
            event_type=event_type,
            offset=(page - 1) * limit,
            limit=limit,
        )
        total = self._event_repository.count_for_user(
            user.id, signal_id=signal_id, dry_run=dry_run, event_type=event_type
        )
        signals = self._signal_repository.list_by_ids({e.signal_id for e in items})
        return EventPage(
            items=items, total=total, signal_types={s.id: s.signal_type for s in signals}
        )


def _to_row(principal: EaPrincipal, event: EaEventIn) -> EaExecutionEvent:
    return EaExecutionEvent(
        user_id=principal.user.id,
        token_id=principal.token.id,
        token_name=principal.token.name,
        signal_id=event.signal_id,
        event_key=event.event_key,
        event_type=event.event_type,
        dry_run=event.dry_run,
        occurred_at=datetime.fromtimestamp(event.occurred_at, UTC),
        account_login=event.account_login,
        broker_symbol=event.broker_symbol,
        order_type=event.order_type,
        order_ticket=event.order_ticket,
        position_id=event.position_id,
        volume=_decimal(event.volume),
        price=_decimal(event.price),
        stop_loss=_decimal(event.stop_loss),
        take_profit=_decimal(event.take_profit),
        profit=_decimal(event.profit),
        currency=event.currency,
        retcode=event.retcode,
        close_reason=event.close_reason,
        message=event.message,
    )


def _decimal(value: float | None) -> Decimal | None:
    # Through `str`, so 4414.236 is stored as 4414.236 and not as the
    # float's binary expansion.
    return None if value is None else Decimal(str(value))


__all__ = ["EaEventService", "EventPage", "IngestResult"]
