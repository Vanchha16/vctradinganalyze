"""Whether a DRAFT signal is confirmed on M15 (ADR-166).

Pure - no DB or I/O. `workers/signal_confirmation_tasks.py` loads the
candles and the M15 Smart Money analysis and owns persistence, the same
split `signal_monitoring_service` has with `signal_monitoring_tasks`.

A draft is an H1 setup that passed every rule, including its higher
timeframes, but is not published yet. It becomes a signal only once M15
breaks structure in its direction - the lower timeframe agreeing that the
move has actually started.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.config import settings
from app.models.enums import SignalStatus, SignalType
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.services.signal_monitoring_service import evaluate_signal_outcome
from app.services.smc.types import BOSEvidence, Direction, SMCAnalysisResult
from app.utils.time import as_aware_utc

#: Also served for a draft that reads as CANCELLED at request time before
#: the task has persisted it, so both paths give the same explanation.
UNCONFIRMED_REASON = "Not confirmed on M15 within the confirmation window."


class ConfirmationOutcome(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ConfirmationDecision:
    outcome: ConfirmationOutcome
    #: What confirmed it, or why it was cancelled. `None` while pending.
    reason: str | None = None


def evaluate(
    signal: Signal,
    candles: Sequence[PriceCandle],
    m15: SMCAnalysisResult | None,
    now: datetime,
) -> ConfirmationDecision:
    """`candles` are M1 candles since the draft was created, oldest first.

    Checked in this order:
    1. **Price already reached the stop loss or take profit** before M15
       confirmed - the setup played out without anyone in it. Cancelled.
       Only candles *before* the confirming break count, so a move that
       confirmed and then ran to target inside one 15-minute gap is still
       confirmed, not cancelled for succeeding.
    2. **M15 broke structure in the signal's direction** after the draft
       was created and inside the window. Confirmed.
    3. **The window has passed.** Cancelled.
    Otherwise it keeps waiting.
    """
    created_at = as_aware_utc(signal.created_at)
    confirming = _first_confirming_break(signal, m15, created_at)
    cutoff = as_aware_utc(confirming.break_time) if confirming is not None else as_aware_utc(now)

    for candle in candles:
        if as_aware_utc(candle.timestamp) >= cutoff:
            break
        outcome = evaluate_signal_outcome(signal, candle)
        if outcome is not None:
            level = "stop loss" if outcome.status is SignalStatus.STOPPED_OUT else "take profit"
            return ConfirmationDecision(
                ConfirmationOutcome.CANCELLED, f"Price reached the {level} before M15 confirmed."
            )

    if confirming is not None:
        return ConfirmationDecision(
            ConfirmationOutcome.CONFIRMED,
            f"M15 broke structure {confirming.direction.value} at "
            f"{confirming.break_price.normalize():f}.",
        )

    window = timedelta(hours=settings.signal_confirmation_window_hours)
    if as_aware_utc(now) - created_at >= window:
        return ConfirmationDecision(ConfirmationOutcome.CANCELLED, UNCONFIRMED_REASON)

    return ConfirmationDecision(ConfirmationOutcome.PENDING)


def _first_confirming_break(
    signal: Signal, m15: SMCAnalysisResult | None, created_at: datetime
) -> BOSEvidence | None:
    """The earliest confirmed M15 break of structure in the signal's
    direction, after the draft was created and before its window closed.

    A break *before* creation is the move the H1 setup was built on, not a
    confirmation of it. A break *after* the window is too late to count,
    even if the task only runs after it."""
    if m15 is None:
        return None
    wanted = Direction.BULLISH if signal.signal_type is SignalType.BUY else Direction.BEARISH
    deadline = created_at + timedelta(hours=settings.signal_confirmation_window_hours)
    breaks = [
        b
        for b in m15.bos
        if b.confirmed
        and b.direction is wanted
        and created_at < as_aware_utc(b.break_time) <= deadline
    ]
    return min(breaks, key=lambda b: as_aware_utc(b.break_time), default=None)


__all__ = [
    "UNCONFIRMED_REASON",
    "ConfirmationDecision",
    "ConfirmationOutcome",
    "evaluate",
]
