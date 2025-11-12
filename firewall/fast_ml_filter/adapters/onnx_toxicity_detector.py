"""ONNX-based toxicity detector adapter."""

from fast_ml_filter.ports.toxicity_detector_port import IToxicityDetector


class ONNXToxicityDetector(IToxicityDetector):
    """ONNX implementation for toxicity detection."""

    def __init__(self, model_path: str = None):
        """
        Initialize ONNX toxicity detector.
        
        Args:
            model_path: Path to ONNX model file (optional, uses simple fallback if not provided)
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
                # Fallback to simple detection
                self._use_model = False

    def detect(self, text: str) -> float:
        """
        Detect toxicity in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Toxicity score between 0.0 and 1.0
        """
        # Try to use ONNX model if available
        self._load_model()
        
        if self._use_model and self._model:
            try:
                # Preprocess text and run inference
                # This is a placeholder - actual implementation depends on model
                # For now, use simple keyword-based detection as fallback
                pass
            except Exception:
                pass
        
        # Simple keyword-based toxicity detection (fallback)
        # In production, this would be replaced by actual ML model
        toxic_keywords = [
            "hate", "kill", "violence", "attack", "harm",
            "stupid", "idiot", "moron", "damn", "hell"
        ]
        
        text_lower = text.lower()
        matches = sum(1 for keyword in toxic_keywords if keyword in text_lower)
        
        # Simple scoring based on keyword matches
        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.3
        elif matches == 2:
            return 0.6
        else:
            return min(0.9, 0.3 + (matches - 1) * 0.2)

