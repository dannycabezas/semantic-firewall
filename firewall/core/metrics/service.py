from __future__ import annotations

from typing import List, Dict, Any

from metrics_manager import MetricsManager, RequestEvent


class MetricsService:
    """
    Facade over `MetricsManager` to expose metrics operations to the API layer without coupling it to the implementation details.

    Args:
        max_requests: Maximum number of requests to store in memory

    Returns:
        MetricsService instance
    """

    def __init__(self, max_requests: int = 500) -> None:
        self._manager = MetricsManager(max_requests=max_requests)

    def add_request(self, event: Dict[str, Any]) -> None:
        """Register a new request event."""
        self._manager.add_request(RequestEvent(**event))

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated executive statistics."""
        return self._manager.get_stats()

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recent requests."""
        return self._manager.get_recent(limit=limit)

    def get_session_analytics(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get session analytics with most suspicious activity."""
        return self._manager.get_session_analytics(top_n=top_n)

    def get_temporal_breakdown(self, minutes: int = 10) -> Dict[str, Any]:
        """Temporal breakdown of risk categories."""
        return self._manager.get_temporal_breakdown(minutes=minutes)


# Global instance; later it can be moved to `core.bootstrap`.
metrics_service = MetricsService(max_requests=500)


