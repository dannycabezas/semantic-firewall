"""Port for alerting."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IAlerter(ABC):
    """Interface for alerting (Slack, webhook, etc.)."""

    @abstractmethod
    def alert(self, severity: str, message: str, context: Dict[str, Any] = None) -> bool:
        """
        Send an alert.
        
        Args:
            severity: Alert severity (low, medium, high, critical)
            message: Alert message
            context: Additional context
            
        Returns:
            True if alert was sent successfully
        """
        pass

