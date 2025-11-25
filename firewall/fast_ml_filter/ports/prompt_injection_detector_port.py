"""Port for prompt injection detection."""

from abc import ABC, abstractmethod
from core.request_context import RequestContext


class IPromptInjectionDetector(ABC):
    """Interface for prompt injection detection."""

    @abstractmethod
    def detect(self, text: str, context: RequestContext | None = None) -> float:
        """
        Detect prompt injection in text.

        Args:
            text: Text to analyze
            context: Request context
        Returns:
            Prompt injection score between 0.0 and 1.0 (1.0 = high confidence prompt injection detected)
        """
        pass
