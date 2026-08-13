"""EA Bot spec §3G/§12: `OrderExecutionService` against
`MockOrderExecutionProvider` - covers the dry-run default (no order
placed), the enabled-execution path (real `BrokerOrder` persisted), and
every skip/reject branch (wrong symbol, max positions reached, sizing
rejected, broker rejection recorded)."""

import uuid
from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.asset import Asset
from app.models.broker_order import BrokerOrder
from app.models.enums import MarketType, OrderStatus, SignalStatus, SignalType, Timeframe
from app.models.signal import Signal
from app.repositories.broker_order_repository import BrokerOrderRepository
from app.services.execution.exceptions import PermanentExecutionError
from app.services.execution.order_execution_service import OrderExecutionService
from app.services.execution.providers.base import OrderPlacementResult
from app.services.execution.providers.mock import MockOrderExecutionProvider

_TABLES = [Asset.__table__, Signal.__table__, BrokerOrder.__table__]
_SYMBOL = "XAUUSDc"


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    with Session(engine) as session:
        yield session


def _make_asset(session: Session, symbol: str = _SYMBOL) -> Asset:
    asset = Asset(symbol=symbol, name="Gold", market_type=MarketType.FOREX)
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


def _make_service(
    session: Session, provider: MockOrderExecutionProvider, *, execution_enabled: bool
) -> OrderExecutionService:
    return OrderExecutionService(
        provider,
        BrokerOrderRepository(session),
        execution_enabled=execution_enabled,
        execution_symbol=_SYMBOL,
        risk_percent=Decimal("3"),
        max_open_positions=1,
    )


def test_dry_run_places_nothing_and_persists_no_order(session: Session) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset)
    provider = MockOrderExecutionProvider()
    service = _make_service(session, provider, execution_enabled=False)

    result = service.process_signal(signal, asset)

    assert result is None
    assert provider.placed_orders == []
    assert session.query(BrokerOrder).count() == 0


def test_enabled_execution_places_order_and_persists_broker_order(session: Session) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset)
    provider = MockOrderExecutionProvider()
    service = _make_service(session, provider, execution_enabled=True)

    result = service.process_signal(signal, asset)

    assert result is not None
    assert result.status == OrderStatus.PENDING
    assert result.signal_id == signal.id
    assert len(provider.placed_orders) == 1
    assert provider.placed_orders[0]["symbol"] == _SYMBOL


def test_skips_signal_for_non_configured_symbol(session: Session) -> None:
    asset = _make_asset(session, symbol="EURUSD")
    signal = _make_signal(session, asset)
    provider = MockOrderExecutionProvider()
    service = _make_service(session, provider, execution_enabled=True)

    result = service.process_signal(signal, asset)

    assert result is None
    assert provider.placed_orders == []


def test_skips_when_max_open_positions_reached(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset)
    provider = MockOrderExecutionProvider()

    from app.services.execution.providers.base import OpenPosition

    monkeypatch.setattr(
        provider,
        "get_open_positions",
        lambda symbol: [
            OpenPosition(
                position_id="1",
                symbol=symbol,
                direction=SignalType.BUY,
                volume=0.1,
                open_price=4400.0,
            )
        ],
    )
    service = _make_service(session, provider, execution_enabled=True)

    result = service.process_signal(signal, asset)

    assert result is None
    assert provider.placed_orders == []


def test_rejected_sizing_places_nothing(session: Session) -> None:
    asset = _make_asset(session)
    # entry == stop_loss -> zero stop distance -> PositionSizingRejectedError
    signal = _make_signal(session, asset, stop_loss=Decimal("4422.00"))
    provider = MockOrderExecutionProvider()
    service = _make_service(session, provider, execution_enabled=True)

    result = service.process_signal(signal, asset)

    assert result is None
    assert provider.placed_orders == []
    assert session.query(BrokerOrder).count() == 0


def test_broker_rejection_is_recorded_as_rejected_order(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset = _make_asset(session)
    signal = _make_signal(session, asset)
    provider = MockOrderExecutionProvider()

    def _raise(**kwargs: object) -> OrderPlacementResult:
        raise PermanentExecutionError("metaapi: trade rejected: market closed")

    monkeypatch.setattr(provider, "place_limit_order", _raise)
    service = _make_service(session, provider, execution_enabled=True)

    result = service.process_signal(signal, asset)

    assert result is not None
    assert result.status == OrderStatus.REJECTED
    assert result.rejection_reason is not None
    assert "market closed" in result.rejection_reason
