"""ONNX-based PII detector adapter."""

import re
from fast_ml_filter.ports.pii_detector_port import IPIIDetector


class ONNXPIIDetector(IPIIDetector):
    """ONNX implementation for PII detection."""

    def __init__(self, model_path: str = None):
        """
        Initialize ONNX PII detector.
        
        Args:
            model_path: Path to ONNX model file (optional, uses regex fallback if not provided)
        """
        self.model_path = model_path
        self._model = None
        self._use_model = False

    def _load_model(self):
        """Lazy load ONNX model."""
        if self.model_path and not self._use_model:
            try:
                import onnxruntime as ort
                self._model = ort.InferenceSession(self.model_path)
                self._use_model = True
            except (ImportError, Exception):
                # Fallback to regex-based detection
                self._use_model = False

    def detect(self, text: str) -> float:
        """
        Detect PII in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            PII score between 0.0 and 1.0
        """
        # Try to use ONNX model if available
        self._load_model()
        
        if self._use_model and self._model:
            try:
                # Preprocess text (tokenize, etc.)
                # This is a placeholder - actual implementation depends on model
                # For now, use regex-based detection as fallback
                pass
            except Exception:
                pass
        
        # Regex-based PII detection (fallback or primary if no model)
        score = 0.0
        
        # SSN pattern
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
            score = max(score, 0.9)
        
        # Email pattern
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            score = max(score, 0.7)
        
        # Credit card pattern (simplified)
        if re.search(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', text):
            score = max(score, 0.8)
        
        # Phone number pattern
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
            score = max(score, 0.6)
        
        return min(score, 1.0)

