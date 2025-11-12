"""Port for PII detection."""

from abc import ABC, abstractmethod


class IPIIDetector(ABC):
    """Interface for PII (Personally Identifiable Information) detection."""

    @abstractmethod
    def detect(self, text: str) -> float:
        """
        Detect PII in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            PII score between 0.0 and 1.0 (1.0 = high confidence PII detected)
        """
        pass

