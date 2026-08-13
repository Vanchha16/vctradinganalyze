"""EA Bot spec §6: a `BrokerOrder`-backed signal's status transitions
are driven by the bridge's real position state, not the candle-simulated
touch logic every other signal uses. `MockOrderExecutionProvider` with
monkeypatched `get_open_positions` stands in for the real bridge."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.broker_order import BrokerOrder
from app.models.enums import MarketType, OrderStatus, SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.repositories.broker_order_repository import BrokerOrderRepository
from app.services.execution.providers.base import OpenPosition
from app.services.execution.providers.mock import MockOrderExecutionProvider
from app.services.execution.reconciliation_service import reconcile_signal

_TABLES = [Asset.__table__, Signal.__table__, BrokerOrder.__table__, PriceCandle.__table__]
_SYMBOL = "XAUUSDc"
_NOW = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _make_asset(session: Session) -> Asset:
    asset = Asset(symbol=_SYMBOL, name="Gold", market_type=MarketType.FOREX)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _make_signal(session: Session, asset: Asset, **overrides: object) -> Signal:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "analysis_id": uuid.uuid4(),
        "asset_id": asset.id,
        "timeframe": Timeframe.H1,
        "signal_type": SignalType.BUY,
        "entry_price": Decimal("4422.00"),
        "stop_loss": Decimal("4400.00"),
        "take_profit": Decimal("4460.00"),
        "risk_reward": 1.7,
        "confidence": 80.0,
        "status": SignalStatus.ACTIVE,
    }
    defaults.update(overrides)
    signal = Signal(**defaults)
    session.add(signal)
    session.commit()
    session.refresh(signal)
    return signal


def _make_broker_order(session: Session, signal: Signal, **overrides: object) -> BrokerOrder:
    defaults: dict[str, object] = {
        "signal_id": signal.id,
        "symbol": _SYMBOL,
        "volume": Decimal("1.0"),
        "requested_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "status": OrderStatus.PENDING,
    }
    defaults.update(overrides)
    order = BrokerOrder(**defaults)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def _make_candle(session: Session, asset: Asset, *, low: str, high: str) -> PriceCandle:
    candle = PriceCandle(
        asset_id=asset.id,
        timeframe=Timeframe.M1,
        timestamp=_NOW,
        open=Decimal(low),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(high),
    )
    session.add(candle)
    session.commit()
    session.refresh(candle)
    return candle


def test_open_position_triggers_active_signal(session: Session) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset, status=SignalStatus.ACTIVE)
    order = _make_broker_order(session, signal, status=OrderStatus.PENDING)
    provider = MockOrderExecutionProvider()
    provider.get_open_positions = lambda symbol: [  # type: ignore[method-assign]
        OpenPosition(
            position_id="pos-1",
            symbol=symbol,
            direction=SignalType.BUY,
            volume=1.0,
            open_price=4423.5,
        )
    ]

    reconcile_signal(signal, order, None, provider, BrokerOrderRepository(session), _NOW)

    assert signal.status == SignalStatus.TRIGGERED
    assert signal.triggered_at is not None
    # SQLite has no native tz-aware storage - `commit()` expires
    # attributes, and the re-fetch comes back naive; compare on the
    # naive wall-clock value only.
    assert signal.triggered_at.replace(tzinfo=None) == _NOW.replace(tzinfo=None)
    assert order.status == OrderStatus.FILLED
    assert order.filled_price == Decimal("4423.5")


def test_no_open_position_leaves_active_signal_unchanged(session: Session) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset, status=SignalStatus.ACTIVE)
    order = _make_broker_order(session, signal, status=OrderStatus.PENDING)
    provider = MockOrderExecutionProvider()  # get_open_positions() -> [] by default

    reconcile_signal(signal, order, None, provider, BrokerOrderRepository(session), _NOW)

    assert signal.status == SignalStatus.ACTIVE
    assert order.status == OrderStatus.PENDING


def test_position_closed_with_take_profit_hit_marks_successful(session: Session) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset, status=SignalStatus.TRIGGERED)
    order = _make_broker_order(
        session, signal, status=OrderStatus.FILLED, filled_price=signal.entry_price
    )
    candle = _make_candle(session, asset, low="4455", high="4465")  # crosses take_profit=4460
    provider = MockOrderExecutionProvider()  # no open positions -> closed

    reconcile_signal(signal, order, candle, provider, BrokerOrderRepository(session), _NOW)

    assert signal.status == SignalStatus.SUCCESSFUL
    assert order.status == OrderStatus.CLOSED
    assert order.closed_at is not None
    assert order.closed_at.replace(tzinfo=None) == _NOW.replace(tzinfo=None)


def test_position_closed_with_stop_loss_hit_marks_stopped_out(session: Session) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset, status=SignalStatus.TRIGGERED)
    order = _make_broker_order(
        session, signal, status=OrderStatus.FILLED, filled_price=signal.entry_price
    )
    candle = _make_candle(session, asset, low="4390", high="4405")  # crosses stop_loss=4400
    provider = MockOrderExecutionProvider()

    reconcile_signal(signal, order, candle, provider, BrokerOrderRepository(session), _NOW)

    assert signal.status == SignalStatus.STOPPED_OUT
    assert order.status == OrderStatus.CLOSED


def test_position_closed_with_no_candle_reference_leaves_signal_unresolved(
    session: Session,
) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset, status=SignalStatus.TRIGGERED)
    order = _make_broker_order(
        session, signal, status=OrderStatus.FILLED, filled_price=signal.entry_price
    )
    provider = MockOrderExecutionProvider()

    reconcile_signal(signal, order, None, provider, BrokerOrderRepository(session), _NOW)

    assert signal.status == SignalStatus.TRIGGERED
    assert order.status == OrderStatus.FILLED


def test_outcome_mismatch_leaves_signal_unresolved_rather_than_guessing(session: Session) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset, status=SignalStatus.TRIGGERED)
    order = _make_broker_order(
        session, signal, status=OrderStatus.FILLED, filled_price=signal.entry_price
    )
    # Candle range that touches neither stop_loss(4400) nor take_profit(4460).
    candle = _make_candle(session, asset, low="4415", high="4430")
    provider = MockOrderExecutionProvider()

    reconcile_signal(signal, order, candle, provider, BrokerOrderRepository(session), _NOW)

    assert signal.status == SignalStatus.TRIGGERED
    assert order.status == OrderStatus.FILLED
