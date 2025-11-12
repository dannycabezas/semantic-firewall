"""Port for toxicity detection."""

from abc import ABC, abstractmethod


class IToxicityDetector(ABC):
    """Interface for toxicity detection."""

    @abstractmethod
    def detect(self, text: str) -> float:
        """
        Detect toxicity in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Toxicity score between 0.0 and 1.0 (1.0 = highly toxic)
        """
        pass

