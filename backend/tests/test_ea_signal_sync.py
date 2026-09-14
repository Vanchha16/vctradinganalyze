"""A live EA's fill and close move the signal it traded (ADR-172)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models.ea_execution_event import EaExecutionEvent
from app.models.enums import SignalStatus, SignalType, Timeframe
from app.models.signal import Signal
from app.services.ea_signal_sync import OTHER_CLOSE_REASON, SignalMove, apply_event

_NOW = datetime(2026, 9, 14, 9, 30, tzinfo=UTC)


def _signal(status: SignalStatus = SignalStatus.ACTIVE) -> Signal:
    """The 2026-09-14 SELL that filled on the broker but not on Twelve Data."""
    return Signal(
        id=uuid.uuid4(),
        analysis_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        timeframe=Timeframe.H1,
        signal_type=SignalType.SELL,
        entry_price=Decimal("4311.262"),
        stop_loss=Decimal("4331.442"),
        take_profit=Decimal("4270.902"),
        risk_reward=2.0,
        confidence=72.0,
        status=status,
        created_at=_NOW - timedelta(hours=1),
    )


def _event(
    event_type: str,
    *,
    dry_run: bool = False,
    at: datetime = _NOW,
    price: str | None = None,
    close_reason: str | None = None,
) -> EaExecutionEvent:
    return EaExecutionEvent(
        event_type=event_type,
        dry_run=dry_run,
        occurred_at=at,
        price=Decimal(price) if price is not None else None,
        close_reason=close_reason,
    )


def test_a_live_fill_marks_an_unfilled_signal_filled_at_the_fill_time() -> None:
    signal = _signal()
    filled_at = _NOW - timedelta(minutes=20)

    change = apply_event(signal, _event("position_opened", at=filled_at))

    assert change is not None
    assert change.move is SignalMove.TRIGGERED
    assert change.has_message
    assert signal.status is SignalStatus.TRIGGERED
    assert signal.triggered_at == filled_at
    # Stop loss and take profit are checked from the fill onwards.
    assert signal.last_monitored_at == filled_at


def test_a_dry_run_report_changes_nothing() -> None:
    signal = _signal()

    assert apply_event(signal, _event("position_opened", dry_run=True)) is None
    assert apply_event(signal, _event("position_closed", dry_run=True, close_reason="tp")) is None
    assert signal.status is SignalStatus.ACTIVE


@pytest.mark.parametrize("event_type", ["order_placed", "order_cancelled", "dry_run_checked"])
def test_reports_other_than_a_fill_or_close_change_nothing(event_type: str) -> None:
    signal = _signal()

    assert apply_event(signal, _event(event_type)) is None
    assert signal.status is SignalStatus.ACTIVE


@pytest.mark.parametrize(
    "status",
    [
        SignalStatus.DRAFT,
        SignalStatus.TRIGGERED,
        SignalStatus.CANCELLED,
        SignalStatus.SUCCESSFUL,
        SignalStatus.STOPPED_OUT,
    ],
)
def test_a_fill_only_moves_an_unfilled_signal(status: SignalStatus) -> None:
    """Already filled on Twelve Data, finished, or cancelled: left as it is."""
    signal = _signal(status)

    assert apply_event(signal, _event("position_opened")) is None
    assert signal.status is status


@pytest.mark.parametrize(
    ("reason", "status", "profit_loss"),
    [
        ("tp", SignalStatus.SUCCESSFUL, Decimal("40.360")),
        ("sl", SignalStatus.STOPPED_OUT, Decimal("-20.180")),
    ],
)
def test_a_take_profit_or_stop_loss_close_finishes_the_signal_with_a_message(
    reason: str, status: SignalStatus, profit_loss: Decimal
) -> None:
    signal = _signal(SignalStatus.TRIGGERED)

    change = apply_event(signal, _event("position_closed", close_reason=reason, price="4000"))

    assert change is not None
    assert change.move is SignalMove.CLOSED
    assert change.has_message
    assert signal.status is status
    assert signal.closed_at == _NOW
    # At the signal's own level, like the candle monitor - not the broker price.
    assert signal.profit_loss == profit_loss


def test_a_hand_close_ends_the_signal_without_a_subscriber_message() -> None:
    """The operator closed the 4311 SELL by hand at 4281.287."""
    signal = _signal(SignalStatus.TRIGGERED)

    change = apply_event(signal, _event("position_closed", close_reason="manual", price="4281.287"))

    assert change is not None
    assert not change.has_message
    assert signal.status is SignalStatus.CLOSED
    assert signal.status_reason == "Closed by hand on the EA's account."
    assert signal.profit_loss == Decimal("29.975")


def test_an_unknown_close_reason_still_ends_the_signal() -> None:
    signal = _signal(SignalStatus.TRIGGERED)

    apply_event(signal, _event("position_closed", close_reason="other"))

    assert signal.status is SignalStatus.CLOSED
    assert signal.status_reason == OTHER_CLOSE_REASON
    assert signal.profit_loss is None  # no close price reported


def test_a_close_whose_fill_was_never_reported_fills_and_closes_the_signal() -> None:
    signal = _signal()

    change = apply_event(signal, _event("position_closed", close_reason="manual", price="4300"))

    assert change is not None
    assert signal.status is SignalStatus.CLOSED
    assert signal.triggered_at == _NOW
    assert signal.closed_at == _NOW


@pytest.mark.parametrize("status", [SignalStatus.CANCELLED, SignalStatus.SUCCESSFUL])
def test_a_close_leaves_a_finished_or_cancelled_signal_alone(status: SignalStatus) -> None:
    signal = _signal(status)

    assert apply_event(signal, _event("position_closed", close_reason="manual")) is None
    assert signal.status is status
    assert signal.closed_at is None
