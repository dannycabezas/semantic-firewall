import asyncio
import logging

from fastapi import FastAPI

from core.realtime import init_event_queue, event_broadcaster
from core.benchmarks import benchmark_service


logger = logging.getLogger(__name__)


def register_startup_events(app: FastAPI) -> None:
    """
    Register startup/shutdown handlers in the FastAPI app.

    Centralize the initialization of infrastructure services
    (realtime, benchmarks, etc.) to keep the endpoint modules
    cleaner.
    """

    @app.on_event("startup")
    async def _on_startup() -> None:  # pragma: no cover - framework hook
        # Initialize event queue and broadcast launcher
        await init_event_queue()
        asyncio.create_task(event_broadcaster())

        # Initialize benchmark system (DB + runner)
        await benchmark_service.initialize()

        logger.info("Startup hooks initialized (realtime + benchmarks)")


