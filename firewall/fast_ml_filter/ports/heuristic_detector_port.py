"""Port for heuristic detection."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IHeuristicDetector(ABC):
    """Interface for heuristic-based detection (regex, patterns, etc.)."""

    @abstractmethod
    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect issues using heuristics.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with detection results:
            - blocked: bool
            - flags: list of detected patterns
            - reason: str (if blocked)
        """
        pass
