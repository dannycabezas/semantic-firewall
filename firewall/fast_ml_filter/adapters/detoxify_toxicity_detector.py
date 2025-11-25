"""Detoxify-based toxicity detector adapter."""

from typing import Optional

from fast_ml_filter.ports.toxicity_detector_port import IToxicityDetector


class DetoxifyToxicityDetector(IToxicityDetector):
    """Detoxify implementation for toxicity detection."""

    def __init__(self, model_name: str = "original", device: Optional[str] = None):
        """
        Initialize Detoxify toxicity detector.

        Args:
            model_name: Model name ('original', 'unbiased', or 'multilingual')
            device: Device to run model on ('cpu', 'cuda', etc.). Defaults to 'cpu'
        """
        self.model_name = model_name
        self.device = device or "cpu"
        self._model = None

    def _load_model(self):
        """Lazy load Detoxify model."""
        if self._model is None:
            try:
                from detoxify import Detoxify
                
                # Initialize Detoxify model
                self._model = Detoxify(self.model_name, device=self.device)
                print(f"Loaded Detoxify model: {self.model_name}")
            except Exception as e:
                print(f"Failed to load Detoxify model: {e}")
                raise

    def detect(self, text: str) -> float:
        """
        Detect toxicity in text using Detoxify.

        Args:
            text: Text to analyze

        Returns:
            Toxicity score between 0.0 and 1.0 (1.0 = highly toxic)
        """
        self._load_model()
        
        try:
            # Get predictions from Detoxify
            results = self._model.predict(text)
            
            # Convert results to a single toxicity score
            # Detoxify returns a dict with different toxicity labels
            if self.model_name == "multilingual":
                # Multilingual model returns 'toxicity' as main label
                toxicity_score = float(results.get("toxicity", 0.0))
            elif self.model_name == "unbiased":
                # Unbiased model returns 'toxicity' as main label
                toxicity_score = float(results.get("toxicity", 0.0))
            else:  # original model
                # Original model has multiple labels: toxic, severe_toxic, obscene, threat, insult, identity_hate
                # We'll use the 'toxic' label as primary, but can combine others
                toxic = float(results.get("toxicity", 0.0))
                severe_toxic = float(results.get("severe_toxicity", 0.0))
                # Combine: take max or weighted average
                toxicity_score = max(toxic, severe_toxic * 1.2)  # Severe toxic weighted more
            
            # Ensure score is between 0.0 and 1.0
            return min(max(toxicity_score, 0.0), 1.0)
            
        except Exception as e:
            print(f"Error during Detoxify inference: {e}. Using fallback.")
            # Fallback: return 0.0 (no toxicity detected) on error
            return 0.0