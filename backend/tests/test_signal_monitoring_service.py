"""Unit tests for TP/SL touch-detection (docs/51 §10's deferred live
monitoring) - pure function, no DB, covers BUY/SELL x hit-TP/hit-SL/no-hit/
both-in-one-candle."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.enums import SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.services.signal_monitoring_service import entry_touched, evaluate_signal_outcome

_TIMESTAMP = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


def _make_signal(*, signal_type: SignalType) -> Signal:
    if signal_type == SignalType.BUY:
        entry, stop_loss, take_profit = Decimal("100"), Decimal("95"), Decimal("115")
    else:
        entry, stop_loss, take_profit = Decimal("100"), Decimal("105"), Decimal("85")
    return Signal(
        id=uuid.uuid4(),
        analysis_id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        timeframe=Timeframe.H1,
        signal_type=signal_type,
        entry_price=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_reward=3.0,
        confidence=80.0,
    )


def _make_candle(*, high: str, low: str) -> PriceCandle:
    return PriceCandle(
        id=uuid.uuid4(),
        asset_id=uuid.uuid4(),
        timeframe=Timeframe.M1,
        timestamp=_TIMESTAMP,
        open=Decimal(high),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(high),
    )


def test_buy_take_profit_hit() -> None:
    signal = _make_signal(signal_type=SignalType.BUY)
    candle = _make_candle(high="116", low="110")

    outcome = evaluate_signal_outcome(signal, candle)

    assert outcome is not None
    assert outcome.status == SignalStatus.SUCCESSFUL
    assert outcome.closed_price == Decimal("115")
    assert outcome.profit_loss == Decimal("15")


def test_buy_stop_loss_hit() -> None:
    signal = _make_signal(signal_type=SignalType.BUY)
    candle = _make_candle(high="99", low="94")

    outcome = evaluate_signal_outcome(signal, candle)

    assert outcome is not None
    assert outcome.status == SignalStatus.STOPPED_OUT
    assert outcome.closed_price == Decimal("95")
    assert outcome.profit_loss == Decimal("-5")


def test_buy_no_hit() -> None:
    signal = _make_signal(signal_type=SignalType.BUY)
    candle = _make_candle(high="105", low="98")

    assert evaluate_signal_outcome(signal, candle) is None


def test_buy_both_levels_touched_stop_loss_takes_precedence() -> None:
    signal = _make_signal(signal_type=SignalType.BUY)
    candle = _make_candle(high="120", low="90")

    outcome = evaluate_signal_outcome(signal, candle)

    assert outcome is not None
    assert outcome.status == SignalStatus.STOPPED_OUT


def test_sell_take_profit_hit() -> None:
    signal = _make_signal(signal_type=SignalType.SELL)
    candle = _make_candle(high="95", low="84")

    outcome = evaluate_signal_outcome(signal, candle)

    assert outcome is not None
    assert outcome.status == SignalStatus.SUCCESSFUL
    assert outcome.closed_price == Decimal("85")
    assert outcome.profit_loss == Decimal("15")


def test_sell_stop_loss_hit() -> None:
    signal = _make_signal(signal_type=SignalType.SELL)
    candle = _make_candle(high="106", low="101")

    outcome = evaluate_signal_outcome(signal, candle)

    assert outcome is not None
    assert outcome.status == SignalStatus.STOPPED_OUT
    assert outcome.closed_price == Decimal("105")
    assert outcome.profit_loss == Decimal("-5")


def test_sell_no_hit() -> None:
    signal = _make_signal(signal_type=SignalType.SELL)
    candle = _make_candle(high="102", low="95")

    assert evaluate_signal_outcome(signal, candle) is None


def test_sell_both_levels_touched_stop_loss_takes_precedence() -> None:
    signal = _make_signal(signal_type=SignalType.SELL)
    candle = _make_candle(high="110", low="80")

    outcome = evaluate_signal_outcome(signal, candle)

    assert outcome is not None
    assert outcome.status == SignalStatus.STOPPED_OUT


def test_entry_touched_true_when_candle_range_covers_entry() -> None:
    signal = _make_signal(signal_type=SignalType.BUY)
    candle = _make_candle(high="102", low="99")

    assert entry_touched(signal, candle) is True


def test_entry_touched_false_when_candle_range_never_reaches_entry() -> None:
    """The production-defect reproduction shape: entry (100) is above the
    entire candle range - price never traded there."""
    signal = _make_signal(signal_type=SignalType.BUY)
    candle = _make_candle(high="99", low="94")

    assert entry_touched(signal, candle) is False


def test_entry_touched_true_at_exact_boundary() -> None:
    signal = _make_signal(signal_type=SignalType.BUY)
    candle = _make_candle(high="100", low="98")

    assert entry_touched(signal, candle) is True
