import asyncio
import logging
from typing import List, Optional

from fastapi import WebSocket


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and heartbeats."""

    def __init__(self) -> None:
        """Initialize the ConnectionManager."""
        self.active_connections: List[WebSocket] = []
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 90  # seconds

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket connected. Total connections: %s",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Delete a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                "WebSocket disconnected. Total connections: %s",
                len(self.active_connections),
            )

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error sending message to websocket: %s", exc)
            self.disconnect(websocket)

    async def broadcast(self, message: dict) -> None:
        """Broadcast to all active connections."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Error broadcasting to websocket: %s", exc)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def heartbeat_sender(self, websocket: WebSocket) -> None:
        """Send periodic heartbeats to a given connection."""
        try:
            while websocket in self.active_connections:
                await asyncio.sleep(self.heartbeat_interval)
                if websocket in self.active_connections:
                    await websocket.send_json({"type": "ping"})
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Heartbeat sender error: %s", exc)
            self.disconnect(websocket)


# Global instance; later it can be moved to `core.bootstrap`.
manager: Optional[ConnectionManager] = ConnectionManager()


