"""Port for feature extraction."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IFeatureExtractor(ABC):
    """Interface for feature extraction."""

    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract features from text.

        Args:
            text: Normalized text input

        Returns:
            Dictionary of extracted features
        """
        pass
