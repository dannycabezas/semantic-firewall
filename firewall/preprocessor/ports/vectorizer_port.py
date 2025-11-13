"""Port for text vectorization."""

from abc import ABC, abstractmethod
from typing import List


class IVectorizer(ABC):
    """Interface for text vectorization."""

    @abstractmethod
    def vectorize(self, text: str) -> List[float]:
        """
        Convert text to embedding vector.

        Args:
            text: Normalized text input

        Returns:
            Embedding vector as list of floats
        """
        pass
