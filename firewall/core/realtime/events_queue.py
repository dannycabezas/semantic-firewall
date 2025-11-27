import asyncio
import logging
from typing import Optional

from .connection_manager import manager


logger = logging.getLogger(__name__)


# Global queue for dashboard events (can be moved to `core.bootstrap` if needed)
event_queue: Optional[asyncio.Queue] = None


async def init_event_queue() -> None:
    """Initialize the global event queue if it doesn't exist."""
    global event_queue
    if event_queue is None:
        event_queue = asyncio.Queue()


async def event_broadcaster() -> None:
    """Background task that sends events from the queue to all WebSocket clients."""
    global event_queue
    while True:
        try:
            if event_queue is None:
                await asyncio.sleep(0.1)
                continue
            event = await event_queue.get()
            if manager:
                await manager.broadcast(event)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error in event broadcaster: %s", exc)


