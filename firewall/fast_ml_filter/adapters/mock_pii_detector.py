"""Mock PII detector for testing."""

from fast_ml_filter.ports.pii_detector_port import IPIIDetector


class MockPIIDetector(IPIIDetector):
    """Mock implementation for PII detection (for testing)."""

    def __init__(self, fixed_score: float = 0.0):
        """
        Initialize mock detector.

        Args:
            fixed_score: Fixed score to return (for testing)
        """
        self.fixed_score = fixed_score

    def detect(self, text: str) -> float:
        """
        Detect PII in text (mock implementation).

        Args:
            text: Text to analyze

        Returns:
            Fixed PII score
        """
        return self.fixed_score
