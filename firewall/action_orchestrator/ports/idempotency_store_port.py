"""Port for idempotency storage."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IIdempotencyStore(ABC):
    """Interface for idempotency storage (Redis, dict, etc.)."""

    @abstractmethod
    def get(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored result for a request ID.

        Args:
            request_id: Unique request identifier

        Returns:
            Stored result or None if not found
        """
        pass

    @abstractmethod
    def store(self, request_id: str, result: Dict[str, Any]) -> bool:
        """
        Store result for a request ID.

        Args:
            request_id: Unique request identifier
            result: Result to store

        Returns:
            True if successful
        """
        pass
