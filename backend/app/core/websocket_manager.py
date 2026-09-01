import asyncio
import uuid
from typing import Any

import jwt
import structlog
from fastapi import WebSocket

from app.core.redis_pubsub import subscribe_channel
from app.core.security import decode_token
from app.database.session import SessionLocal
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


def authenticate_websocket_token(token: str | None) -> User | None:
    """Validate a JWT access token for WebSocket authentication.

    Returns the active `User` if valid and active, or `None` if invalid/inactive.
    """
    if not token:
        return None

    try:
        claims = decode_token(token)
    except jwt.PyJWTError:
        return None

    if claims.get("type") != "access":
        return None

    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError):
        return None

    session = SessionLocal()
    try:
        user = UserRepository(session).get_by_id(user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            return None
        return user
    except Exception as exc:
        logger.warning("websocket.auth_db_error", error=str(exc))
        return None
    finally:
        session.close()


class WebSocketConnectionManager:
    """Manages active WebSocket connections, groups them by topic/channel,
    and bridges Redis Pub/Sub streams to connected clients."""

    def __init__(self) -> None:
        self._active_connections: dict[str, set[WebSocket]] = {}
        self._listener_tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Accept a connection and register it under the given channel."""
        await websocket.accept()
        async with self._lock:
            if channel not in self._active_connections:
                self._active_connections[channel] = set()
            self._active_connections[channel].add(websocket)

            # Start a Redis listener background task for this channel if not already running
            if channel not in self._listener_tasks or self._listener_tasks[channel].done():
                self._listener_tasks[channel] = asyncio.create_task(
                    self._redis_listener(channel)
                )

        logger.info(
            "websocket.connected",
            channel=channel,
            active_count=len(self._active_connections[channel]),
        )

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        """Unregister a disconnected WebSocket and cleanup idle Redis listeners."""
        async with self._lock:
            if channel in self._active_connections:
                self._active_connections[channel].discard(websocket)
                if not self._active_connections[channel]:
                    del self._active_connections[channel]
                    # Cancel Redis listener if no clients remain on this channel
                    if channel in self._listener_tasks:
                        self._listener_tasks[channel].cancel()
                        del self._listener_tasks[channel]

        logger.info("websocket.disconnected", channel=channel)

    async def broadcast_to_channel(self, channel: str, message: Any) -> None:
        """Broadcast a message directly to all active WebSockets on a channel."""
        async with self._lock:
            sockets = list(self._active_connections.get(channel, []))

        dead_sockets: list[WebSocket] = []
        for socket in sockets:
            try:
                if isinstance(message, dict):
                    await socket.send_json(message)
                else:
                    await socket.send_text(str(message))
            except Exception:
                dead_sockets.append(socket)

        if dead_sockets:
            async with self._lock:
                for socket in dead_sockets:
                    if channel in self._active_connections:
                        self._active_connections[channel].discard(socket)

    async def _redis_listener(self, channel: str) -> None:
        """Listen to a Redis channel and fan-out received messages to WebSockets."""
        try:
            async for message in subscribe_channel(channel):
                await self.broadcast_to_channel(channel, message)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("websocket.redis_listener_error", channel=channel, error=str(exc))


ws_manager = WebSocketConnectionManager()
