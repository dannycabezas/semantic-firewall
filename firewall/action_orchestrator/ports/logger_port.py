"""Port for logging."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class ILogger(ABC):
    """Interface for logging."""

    @abstractmethod
    def log(self, level: str, message: str, **kwargs) -> None:
        """
        Log a message.
        
        Args:
            level: Log level (info, warning, error, debug)
            message: Log message
            **kwargs: Additional context
        """
        pass

    @abstractmethod
    def log_structured(self, data: Dict[str, Any]) -> None:
        """
        Log structured data.
        
        Args:
            data: Dictionary of structured data
        """
        pass

