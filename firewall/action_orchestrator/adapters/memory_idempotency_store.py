"""Memory-based idempotency store adapter (mock for POC)."""

from typing import Any, Dict, Optional

from action_orchestrator.ports.idempotency_store_port import IIdempotencyStore


class MemoryIdempotencyStore(IIdempotencyStore):
    """In-memory idempotency store implementation (mock for POC)."""

    def __init__(self):
        """Initialize idempotency store."""
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored result for a request ID.

        Args:
            request_id: Unique request identifier

        Returns:
            Stored result or None if not found
        """
        return self._store.get(request_id)

    def store(self, request_id: str, result: Dict[str, Any]) -> bool:
        """
        Store result for a request ID.

        Args:
            request_id: Unique request identifier
            result: Result to store

        Returns:
            True if successful
        """
        try:
            self._store[request_id] = result.copy()
            return True
        except Exception:
            return False
