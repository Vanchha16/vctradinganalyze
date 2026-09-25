"""A live EA's fill and close move the signal it traded (ADR-172).

The website follows a signal's entry and exit on Twelve Data candles, which
can sit a few tenths away from the broker's own prices. On 2026-09-14 the EA's
sell limit at 4311.26 filled on the broker while Twelve Data's high was
4310.90, so the website kept the signal "not filled" and later replaced a trade
that had already filled and closed. A fill the account really made now counts.

One direction only: a live account's fill or close moves an open signal. A
signal the website already finished or cancelled is left alone, and nothing
here un-fills a signal whose order never filled.

Pure - `EaEventService.ingest` owns persistence and messages.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.models.ea_execution_event import EaExecutionEvent
from app.models.enums import SignalStatus, SignalType
from app.models.signal import Signal
from app.services.smc_crt.execution_safety import EXECUTION_REJECTED_REASON, SMC_STRATEGY_NAME
from app.utils.time import as_aware_utc

#: Closes where price reached the signal's own level.
_LEVEL_CLOSES = {"tp": SignalStatus.SUCCESSFUL, "sl": SignalStatus.STOPPED_OUT}
#: `status_reason` for every other close, which ends as CLOSED.
_OTHER_CLOSE_REASONS = {
    "manual": "Closed by hand on the EA's account.",
    "stop_out": "Closed by a margin stop-out on the EA's account.",
}
OTHER_CLOSE_REASON = "Closed on the EA's account before take profit or stop loss."


class SignalMove(StrEnum):
    TRIGGERED = "triggered"
    CLOSED = "closed"
    #: ADR-183 audit D3: a live EA refused an smc-ict-crt-v1 order. Never a
    #: subscriber message (`has_message` is always False): nothing traded, and
    #: the operator already gets the EA's own rejection alert.
    EXECUTION_REJECTED = "execution_rejected"


@dataclass(frozen=True, slots=True)
class SignalChange:
    signal_id: uuid.UUID
    move: SignalMove
    #: Whether subscribers get a message for it: a fill, or a take profit or
    #: stop loss. The outcome message only knows those two exits, so any other
    #: close changes the website only - the operator has the EA's own alert.
    has_message: bool
    occurred_at: datetime


def apply_event(signal: Signal, event: EaExecutionEvent) -> SignalChange | None:
    """Moves `signal` for a live `position_opened` or `position_closed`
    report and says what moved; `None` when the report changes nothing."""
    rejection = _execution_rejection(signal, event)
    if rejection is not None:
        return rejection
    if event.dry_run or event.event_type not in ("position_opened", "position_closed"):
        return None
    at = as_aware_utc(event.occurred_at)

    if event.event_type == "position_opened":
        if signal.status is not SignalStatus.ACTIVE:
            return None
        _trigger(signal, at)
        return SignalChange(signal.id, SignalMove.TRIGGERED, has_message=True, occurred_at=at)

    if signal.status is SignalStatus.ACTIVE:
        # The fill was never reported (EA 1.30 missed some): it filled no
        # later than it closed.
        _trigger(signal, at)
    elif signal.status is not SignalStatus.TRIGGERED:
        return None

    reason = event.close_reason or ""
    status = _LEVEL_CLOSES.get(reason, SignalStatus.CLOSED)
    if status is SignalStatus.SUCCESSFUL:
        closed_price: Decimal | None = signal.take_profit
    elif status is SignalStatus.STOPPED_OUT:
        closed_price = signal.stop_loss
    else:
        closed_price = event.price
        signal.status_reason = _OTHER_CLOSE_REASONS.get(reason, OTHER_CLOSE_REASON)

    signal.status = status
    signal.closed_at = at
    signal.last_monitored_at = at
    signal.profit_loss = _profit_loss(signal, closed_price)
    return SignalChange(
        signal.id,
        SignalMove.CLOSED,
        has_message=status is not SignalStatus.CLOSED,
        occurred_at=at,
    )


def _execution_rejection(signal: Signal, event: EaExecutionEvent) -> SignalChange | None:
    """ADR-183 audit D3/D4. A live EA that could not place an smc-ict-crt-v1
    order (`order_rejected` by the broker, `order_skipped` by the EA) leaves a
    signal that no broker ever held. Left ACTIVE, the M1 monitor would later
    record a fill and a stop-out for it, and it would hold the one-trade
    capacity; so it is cancelled here, at once, with an unambiguous reason.

    Scoped to smc-ict-crt-v1 on purpose: every other strategy's handling of
    these events is unchanged. Dry-run reports are checks, not executions,
    and are left alone."""
    if (
        event.dry_run
        or event.event_type not in ("order_rejected", "order_skipped")
        or signal.strategy != SMC_STRATEGY_NAME
        or signal.status is not SignalStatus.ACTIVE
    ):
        return None
    at = as_aware_utc(event.occurred_at)
    detail = event.message or (f"retcode {event.retcode}" if event.retcode is not None else "")
    signal.status = SignalStatus.CANCELLED
    signal.closed_at = at
    signal.status_reason = f"{EXECUTION_REJECTED_REASON}: {event.event_type} {detail}".strip()[:160]
    return SignalChange(signal.id, SignalMove.EXECUTION_REJECTED, has_message=False, occurred_at=at)


def _trigger(signal: Signal, at: datetime) -> None:
    signal.status = SignalStatus.TRIGGERED
    signal.triggered_at = at
    # Monitoring checks stop loss and take profit from the fill onwards.
    signal.last_monitored_at = at


def _profit_loss(signal: Signal, closed_price: Decimal | None) -> Decimal | None:
    """In price, like the candle monitor's outcome - not the account's money."""
    if closed_price is None:
        return None
    move = Decimal(closed_price) - Decimal(signal.entry_price)
    return move if signal.signal_type is SignalType.BUY else -move


__all__ = ["OTHER_CLOSE_REASON", "SignalChange", "SignalMove", "apply_event"]
