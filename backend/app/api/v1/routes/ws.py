import asyncio
from typing import Annotated

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.core.redis_pubsub import get_price_channel, get_signal_channel
from app.core.websocket_manager import authenticate_websocket_token, ws_manager
from app.models.enums import Timeframe

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["websockets"])


@router.websocket("/ws/prices")
async def websocket_prices(
    websocket: WebSocket,
    symbol: Annotated[str, Query(description="Asset symbol to subscribe to, e.g. BTCUSD")],
    timeframe: Annotated[str, Query(description="Timeframe, e.g. m1, h1, d1")] = "m1",
    token: Annotated[str | None, Query(description="JWT access token")] = None,
) -> None:
    """Stream real-time price candle ticks for an asset symbol and timeframe."""
    # `authenticate_websocket_token` opens a blocking sync DB session -
    # run it off the event loop so one auth check can't stall every other
    # WebSocket/HTTP request on this worker.
    user = await asyncio.to_thread(authenticate_websocket_token, token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    try:
        tf_enum = Timeframe(timeframe.lower())
    except ValueError:
        await websocket.close(
            code=status.WS_1003_UNSUPPORTED_DATA,
            reason=f"Invalid timeframe: {timeframe}",
        )
        return

    channel = get_price_channel(symbol, tf_enum.value)
    await ws_manager.connect(websocket, channel)

    try:
        while True:
            # Handle client-initiated messages (e.g. ping/pong keepalive)
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, channel)
    except Exception as exc:
        logger.warning(
            "websocket.price_stream_error",
            symbol=symbol,
            timeframe=timeframe,
            error=str(exc),
        )
        await ws_manager.disconnect(websocket, channel)


@router.websocket("/ws/signals")
async def websocket_signals(
    websocket: WebSocket,
    token: Annotated[str | None, Query(description="JWT access token")] = None,
) -> None:
    """Stream real-time trading signal updates (new signals, triggered status, TP/SL hit)."""
    # `authenticate_websocket_token` opens a blocking sync DB session -
    # run it off the event loop so one auth check can't stall every other
    # WebSocket/HTTP request on this worker.
    user = await asyncio.to_thread(authenticate_websocket_token, token)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    channel = get_signal_channel()
    await ws_manager.connect(websocket, channel)

    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, channel)
    except Exception as exc:
        logger.warning("websocket.signal_stream_error", error=str(exc))
        await ws_manager.disconnect(websocket, channel)
