from dataclasses import dataclass
from typing import Protocol

from app.models.enums import SignalType


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    """Live broker account state (EA Bot spec §5/§7). `balance`/`equity`
    are in whatever unit the account itself is denominated in - for a
    Standard Cent account, that unit is cents-as-currency, not USD; there
    is no separate raw-vs-converted flag to check, `currency` already
    tells the caller what unit these numbers are in (confirmed against
    the real `metaapi-cloud-sdk` `MetatraderAccountInformation` model,
    2026-08-13)."""

    balance: float
    equity: float
    currency: str


@dataclass(frozen=True, slots=True)
class SymbolSpecification:
    """Real per-symbol contract terms (EA Bot spec §5/§7) - lot size and
    pip value are broker/symbol-specific, never assumed from general MT5
    knowledge. Field names/semantics match `metaapi-cloud-sdk`'s real
    `MetatraderSymbolSpecification` model (`contractSize`, `volumeStep`,
    `minVolume`, `maxVolume`, `tickSize`), confirmed 2026-08-13."""

    symbol: str
    contract_size: float
    volume_step: float
    min_volume: float
    max_volume: float
    tick_size: float


@dataclass(frozen=True, slots=True)
class OpenPosition:
    """A currently-open position on the broker account (EA Bot spec §3D's
    "already has an open position" pre-order check, and §6's
    reconciliation fork)."""

    position_id: str
    symbol: str
    direction: SignalType
    volume: float
    open_price: float


@dataclass(frozen=True, slots=True)
class OrderPlacementResult:
    """What placing a real pending limit order returns (EA Bot spec §3B -
    persisted onto the new `BrokerOrder` row by the caller)."""

    broker_order_id: str
    requested_price: float


class OrderExecutionProvider(Protocol):
    """Interface every order-execution provider implements (EA Bot spec
    §1/§2). `OrderExecutionService` depends only on this interface, never
    on a concrete provider class - same separation
    `MarketDataProvider`/`MarketDataService` already establish in this
    codebase. Unlike market data, exactly one provider is ever active at
    a time (`app/dependencies/execution.py`) - no failover chain, since a
    fallback firing after a partial failure could double-place a real
    order.
    """

    name: str

    def get_account_snapshot(self) -> AccountSnapshot:
        """Live balance/equity - never cached long-term (§5). Raises
        `AccountDataUnavailableError` if it cannot be fetched."""
        ...

    def get_symbol_specification(self, symbol: str) -> SymbolSpecification:
        """Raises `SymbolSpecificationUnavailableError` if it cannot be
        fetched."""
        ...

    def get_open_positions(self, symbol: str) -> list[OpenPosition]:
        """Positions currently open for `symbol` on this account (§3D)."""
        ...

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
        """Places a real pending limit order with attached SL/TP (§4.1).
        Callers must only invoke this when `settings.execution_enabled`
        is `True` (§0.6/§0.9/§12) - the provider itself does not
        re-check the kill switch, that gate lives one layer up in
        `OrderExecutionService` so it is enforced in exactly one place."""
        ...

    def health_check(self) -> bool:
        """A cheap liveness check - does not place or fetch trade data."""
        ...


__all__ = [
    "AccountSnapshot",
    "OpenPosition",
    "OrderExecutionProvider",
    "OrderPlacementResult",
    "SymbolSpecification",
]
