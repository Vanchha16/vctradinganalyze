import asyncio
from typing import Any

import structlog
from metaapi_cloud_sdk import MetaApi
from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

from app.models.enums import SignalType
from app.services.execution.exceptions import (
    AccountDataUnavailableError,
    PermanentExecutionError,
    SymbolSpecificationUnavailableError,
    TransientExecutionError,
)
from app.services.execution.providers.base import (
    AccountSnapshot,
    OpenPosition,
    OrderPlacementResult,
    SymbolSpecification,
)

logger = structlog.get_logger(__name__)

#: MT5 position type strings (real values from `metaapi-cloud-sdk`'s
#: `MetatraderPosition.type`, confirmed 2026-08-13) - not assumed.
_POSITION_TYPE_BUY = "POSITION_TYPE_BUY"


class MetaApiOrderExecutionProvider:
    """Real order-execution provider backed by MetaApi.cloud
    (.claude/specs/phase-11-ea-bot-exness-mt5-execution.md §2).

    The `metaapi-cloud-sdk` package is entirely `asyncio`-based (its
    connection is a persistent websocket, not a per-call REST client) -
    this codebase's services/Celery tasks are synchronous, so each
    public method here opens a short-lived event loop via `asyncio.run`
    and does the connect -> synchronize -> call -> close sequence within
    it. This trades a small per-call reconnect cost (acceptable at this
    system's call volume - a handful of calls per signal, not a
    high-frequency loop) for not introducing async infrastructure into
    an otherwise-sync codebase (§1's "additive, not a rewrite" rule).
    """

    name = "metaapi"

    def __init__(self, token: str, account_id: str, *, timeout_seconds: float = 30.0) -> None:
        self._token = token
        self._account_id = account_id
        self._timeout_seconds = timeout_seconds

    def get_account_snapshot(self) -> AccountSnapshot:
        try:
            return asyncio.run(self._get_account_snapshot_async())
        except AccountDataUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 - bridge/network failures, not ours to classify further
            raise AccountDataUnavailableError(
                f"metaapi: failed to fetch account information: {exc}"
            ) from exc

    def get_symbol_specification(self, symbol: str) -> SymbolSpecification:
        try:
            return asyncio.run(self._get_symbol_specification_async(symbol))
        except SymbolSpecificationUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SymbolSpecificationUnavailableError(
                f"metaapi: failed to fetch symbol specification for {symbol!r}: {exc}"
            ) from exc

    def get_open_positions(self, symbol: str) -> list[OpenPosition]:
        try:
            return asyncio.run(self._get_open_positions_async(symbol))
        except Exception as exc:  # noqa: BLE001
            raise TransientExecutionError(
                f"metaapi: failed to fetch open positions: {exc}"
            ) from exc

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
        try:
            return asyncio.run(
                self._place_limit_order_async(
                    symbol=symbol,
                    direction=direction,
                    volume=volume,
                    open_price=open_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
            )
        except TradeException as exc:
            # A broker-rejected trade (bad price, market closed, symbol
            # disabled) is not worth retrying - surfaced as permanent so
            # `OrderExecutionService` records it on the `BrokerOrder` row
            # (`status=REJECTED`, `rejection_reason`) rather than retrying
            # against a real account.
            raise PermanentExecutionError(f"metaapi: trade rejected: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise TransientExecutionError(f"metaapi: order placement failed: {exc}") from exc

    def health_check(self) -> bool:
        try:
            asyncio.run(self._health_check_async())
            return True
        except Exception:  # noqa: BLE001 - liveness check, any failure means "not healthy"
            logger.warning("metaapi_provider.health_check_failed", exc_info=True)
            return False

    # --- Internal async implementation ----------------------------------

    async def _connection(self) -> Any:  # noqa: ANN401 - untyped/no py.typed marker in metaapi-cloud-sdk
        api = MetaApi(self._token)
        account = await api.metatrader_account_api.get_account(self._account_id)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized(timeout_in_seconds=self._timeout_seconds)
        return connection

    async def _get_account_snapshot_async(self) -> AccountSnapshot:
        connection = await self._connection()
        info = await connection.get_account_information()
        return AccountSnapshot(
            balance=float(info["balance"]),
            equity=float(info["equity"]),
            currency=str(info["currency"]),
        )

    async def _get_symbol_specification_async(self, symbol: str) -> SymbolSpecification:
        connection = await self._connection()
        spec = await connection.get_symbol_specification(symbol)
        return SymbolSpecification(
            symbol=symbol,
            contract_size=float(spec["contractSize"]),
            volume_step=float(spec["volumeStep"]),
            min_volume=float(spec["minVolume"]),
            max_volume=float(spec["maxVolume"]),
            tick_size=float(spec["tickSize"]),
        )

    async def _get_open_positions_async(self, symbol: str) -> list[OpenPosition]:
        connection = await self._connection()
        positions = await connection.get_positions()
        return [
            OpenPosition(
                position_id=str(position["id"]),
                symbol=position["symbol"],
                direction=(
                    SignalType.BUY if position["type"] == _POSITION_TYPE_BUY else SignalType.SELL
                ),
                volume=float(position["volume"]),
                open_price=float(position["openPrice"]),
            )
            for position in positions
            if position["symbol"] == symbol
        ]

    async def _place_limit_order_async(
        self,
        *,
        symbol: str,
        direction: SignalType,
        volume: float,
        open_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> OrderPlacementResult:
        connection = await self._connection()
        create = (
            connection.create_limit_buy_order
            if direction == SignalType.BUY
            else connection.create_limit_sell_order
        )
        result = await create(symbol, volume, open_price, stop_loss, take_profit)
        return OrderPlacementResult(
            broker_order_id=str(result["orderId"]), requested_price=open_price
        )

    async def _health_check_async(self) -> None:
        connection = await self._connection()
        await connection.get_account_information()


__all__ = ["MetaApiOrderExecutionProvider"]
