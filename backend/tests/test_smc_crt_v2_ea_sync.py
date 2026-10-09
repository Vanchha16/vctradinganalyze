"""ADR-185 - the live-EA rules of ADR-183 D3/D10 apply to v2 signals; v1's
behaviour and wording are unchanged; other strategies stay out of scope."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.ea_execution_event import EaExecutionEvent
from app.models.enums import SignalStatus, SignalType, Timeframe
from app.models.signal import Signal
from app.services.ea_signal_sync import EA_CANCELLED_REASON, SignalMove, apply_event
from app.services.smc_crt.execution_safety import EXECUTION_REJECTED_REASON

AT = datetime(2026, 10, 9, 12, tzinfo=UTC)


def _signal(strategy: str) -> Signal:
    return Signal(timeframe=Timeframe.M5, signal_type=SignalType.BUY, entry_price=Decimal("2002"),
                  stop_loss=Decimal("1990"), take_profit=Decimal("2030"), risk_reward=2.3,
                  confidence=0.0, strategy=strategy, status=SignalStatus.ACTIVE)


def _event(event_type: str, *, message: str = "", dry_run: bool = False) -> EaExecutionEvent:
    return EaExecutionEvent(event_type=event_type, dry_run=dry_run, occurred_at=AT,
                            message=message, retcode=10016)


def test_a_live_rejection_cancels_a_v2_signal():
    signal = _signal("smc_ict_crt_v2_a")
    change = apply_event(signal, _event("order_rejected", message="Invalid stops"))
    assert change is not None and change.move is SignalMove.EXECUTION_REJECTED
    assert signal.status is SignalStatus.CANCELLED
    assert signal.status_reason.startswith(EXECUTION_REJECTED_REASON)


def test_an_ea_withdrawn_v2_order_uses_v2_wording_and_v1_keeps_its_own():
    v2, v1 = _signal("smc_ict_crt_v2_a"), _signal("smc_ict_crt_v1")
    for signal in (v2, v1):
        change = apply_event(signal, _event("order_cancelled", message="signal closed"))
        assert change is not None and change.move is SignalMove.CANCELLED
    assert v2.status_reason.startswith("smc-ict-crt-v2-a: unfilled order cancelled by the EA")
    assert v1.status_reason.startswith(EA_CANCELLED_REASON)


@pytest.mark.parametrize("strategy", ["bbma", None])
def test_other_strategies_are_still_out_of_scope(strategy):
    signal = _signal(strategy)
    assert apply_event(signal, _event("order_rejected")) is None
    assert signal.status is SignalStatus.ACTIVE


def test_dry_run_reports_never_move_a_v2_signal():
    signal = _signal("smc_ict_crt_v2_a")
    assert apply_event(signal, _event("order_rejected", dry_run=True)) is None
    assert signal.status is SignalStatus.ACTIVE
