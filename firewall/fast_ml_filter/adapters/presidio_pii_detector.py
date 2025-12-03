"""Presidio-based PII detector adapter."""

from fast_ml_filter.ports.pii_detector_port import IPIIDetector
from core.utils.decorators import log_execution_time


class PresidioPIIDetector(IPIIDetector):
    """Presidio implementation for PII detection."""

    def __init__(self):
        """Initialize Presidio detector."""
        self._analyzer = None
        self._available = False
        self._init_presidio()

    @log_execution_time()
    def _init_presidio(self):
        """Initialize Presidio analyzer."""
        try:
            from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

            print("Loading Presidio PII detector...")
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(languages=["en"])

            # Initialize the engine with this specific registry
            self._analyzer = AnalyzerEngine(
                registry=registry, 
                supported_languages=["en"]
            )
            self._available = True
            print("✅ Presidio PII detector initialized")
        except ImportError:
            print(
                "⚠️ Presidio not available. Install with: pip install presidio-analyzer"
            )
            self._available = False
        except Exception as e:
            print(f"⚠️ Failed to initialize Presidio: {e}")
            self._available = False

    @log_execution_time()
    def detect(self, text: str) -> float:
        """
        Detect PII in text using Presidio.

        Args:
            text: Text to analyze

        Returns:
            PII score between 0.0 and 1.0
        """
        if not self._available or not self._analyzer:
            return self._regex_fallback(text)

        try:
            results = self._analyzer.analyze(text=text, language="en")

            if not results:
                return 0.0

            # Calcular score basado en número y tipo de entidades detectadas
            # Ponderar por tipo de PII (SSN > Credit Card > Email > Phone)
            score = 0.0
            for result in results:
                entity_type = result.entity_type
                if entity_type in ["US_SSN", "CREDIT_CARD"]:
                    score = max(score, 0.9)
                elif entity_type == "EMAIL_ADDRESS":
                    score = max(score, 0.7)
                elif entity_type == "PHONE_NUMBER":
                    score = max(score, 0.6)
                elif entity_type in ["PERSON", "LOCATION", "DATE_TIME"]:
                    score = max(score, 0.5)
                else:
                    score = max(score, 0.4)

            return min(score, 1.0)
        except Exception as e:
            print(f"⚠️ Presidio error: {e}. Using fallback.")
            return self._regex_fallback(text)

    def _regex_fallback(self, text: str) -> float:
        """Fallback regex detection."""
        import re

        score = 0.0

        # SSN pattern
        if re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
            score = max(score, 0.9)

        # Credit card pattern
        if re.search(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", text):
            score = max(score, 0.8)

        # Email pattern
        if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text):
            score = max(score, 0.7)

        # Phone number pattern
        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", text):
            score = max(score, 0.6)

        return score
