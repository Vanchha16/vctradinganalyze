"""Cancelling a signal from the website (ADR-169).

Only a signal that has not filled can be cancelled: a draft (never sent) or an
ACTIVE signal (sent, order not filled). A TRIGGERED signal is a live trade -
cancelling the signal would not close the trade in MetaTrader 5, so the
request is refused rather than leave the website and the account disagreeing.

The route owns the side effects after commit (live event, Telegram), the same
split `signal_confirmation_tasks` uses, so this stays free of Celery and Redis.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.exceptions import ConflictException, ResourceNotFoundException
from app.models.audit_log import AuditLog
from app.models.enums import SignalStatus
from app.models.signal import Signal
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.signal_repository import SignalRepository
from app.services.signal.status_resolver import effective_status

MANUAL_CANCEL_REASON = "Cancelled from the website before it filled."

_CANCELLABLE = frozenset({SignalStatus.DRAFT, SignalStatus.ACTIVE})


@dataclass(frozen=True, slots=True)
class CancellationResult:
    signal: Signal
    #: The signal had been published (ACTIVE): Telegram subscribers and the EA
    #: had it, so they must hear it is cancelled. A draft reached no one.
    was_published: bool


class SignalCancellationService:
    def __init__(
        self,
        *,
        signal_repository: SignalRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._signal_repository = signal_repository
        self._audit_log_repository = audit_log_repository

    def cancel(self, actor: User, signal_id: uuid.UUID, now: datetime) -> CancellationResult:
        signal = self._signal_repository.get_by_id(signal_id)
        if signal is None:
            raise ResourceNotFoundException(f"Unknown signal id: {signal_id}")

        # Read-time status: an ACTIVE row past its TTL is already expired and
        # a DRAFT past its window already cancelled (ADR-088/166).
        status = effective_status(
            signal.status, signal.created_at, now, triggered_at=signal.triggered_at
        )
        if status is SignalStatus.TRIGGERED:
            raise ConflictException(
                "This signal's trade is already live. Close the trade in MetaTrader 5 - "
                "cancelling the signal would not close it."
            )
        if status not in _CANCELLABLE:
            label = status.value.replace("_", " ")
            raise ConflictException(f"This signal is already {label} and cannot be cancelled.")

        signal.status = SignalStatus.CANCELLED
        signal.status_reason = MANUAL_CANCEL_REASON
        self._audit_log_repository.create(
            AuditLog(
                user_id=actor.id,
                action="signal.cancel",
                resource="signal",
                resource_id=signal.id,
                context={"previous_status": status.value},
            )
        )
        self._signal_repository.commit()
        return CancellationResult(signal=signal, was_published=status is SignalStatus.ACTIVE)


__all__ = ["MANUAL_CANCEL_REASON", "CancellationResult", "SignalCancellationService"]
