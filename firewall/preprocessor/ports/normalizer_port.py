"""Port for text normalization."""

from abc import ABC, abstractmethod


class INormalizer(ABC):
    """Interface for text normalization."""

    @abstractmethod
    def normalize(self, text: str) -> str:
        """
        Normalize text.

        Args:
            text: Raw text input

        Returns:
            Normalized text
        """
        pass
