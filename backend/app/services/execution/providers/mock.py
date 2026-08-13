import uuid

from app.models.enums import SignalType
from app.services.execution.providers.base import (
    AccountSnapshot,
    OpenPosition,
    OrderPlacementResult,
    SymbolSpecification,
)

#: Deterministic synthetic values for local dev/tests (mirrors
#: `MockMarketDataProvider`'s "never fails, never calls an external
#: service" contract) - a Standard-Cent-account-shaped balance so
#: position-sizing code exercises the same unit-handling path it will
#: hit against the real account, not a USD-shaped number that would
#: silently hide a unit-conversion bug.
_MOCK_BALANCE = 100_000.0
_MOCK_CURRENCY = "USC"
_MOCK_SYMBOL_SPEC = SymbolSpecification(
    symbol="XAUUSDc",
    contract_size=100.0,
    volume_step=0.01,
    min_volume=0.01,
    max_volume=100.0,
    tick_size=0.01,
)


class MockOrderExecutionProvider:
    """Never places a real order, never calls an external service - the
    only provider local dev/tests may use (EA Bot spec §1's safe-mode
    convention, same reasoning as `MockMarketDataProvider`/
    `scripts/run_dev.py`'s existing safe-mode default). Records placed
    orders in-memory only, purely for test assertions."""

    name = "mock"

    def __init__(self) -> None:
        self.placed_orders: list[dict[str, object]] = []

    def get_account_snapshot(self) -> AccountSnapshot:
        return AccountSnapshot(balance=_MOCK_BALANCE, equity=_MOCK_BALANCE, currency=_MOCK_CURRENCY)

    def get_symbol_specification(self, symbol: str) -> SymbolSpecification:
        return _MOCK_SYMBOL_SPEC

    def get_open_positions(self, symbol: str) -> list[OpenPosition]:
        return []

    def place_limit_order(
        self,
        *,
        symbol: str,
        direction: SignalType,
        volume: float,
        open_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> OrderPlacementResult:
        broker_order_id = f"mock-{uuid.uuid4()}"
        self.placed_orders.append(
            {
                "broker_order_id": broker_order_id,
                "symbol": symbol,
                "direction": direction,
                "volume": volume,
                "open_price": open_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            }
        )
        return OrderPlacementResult(broker_order_id=broker_order_id, requested_price=open_price)

    def health_check(self) -> bool:
        return True
