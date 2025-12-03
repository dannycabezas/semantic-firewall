"""
Native Transformers implementation for toxicity detection.
Replaces the 'detoxify' library wrapper to resolve dependency conflicts.
"""

from typing import Optional, Dict, Any
from fast_ml_filter.ports.toxicity_detector_port import IToxicityDetector

class DetoxifyToxicityDetector(IToxicityDetector):
    """
    Toxicity detector using Unitary AI models directly via HuggingFace Transformers.
    """

    # Mapping of the 'detoxify' names to the actual models in Hugging Face
    MODEL_MAP = {
        "original": "unitary/toxic-bert",
        "unbiased": "unitary/unbiased-toxic-roberta",
        "multilingual": "unitary/multilingual-toxic-xlm-roberta"
    }

    def __init__(self, model_name: str = "original", device: Optional[str] = None):
        """
        Initialize toxicity detector.

        Args:
            model_name: 'original', 'unbiased', or 'multilingual'
            device: 'cpu' or 'cuda'
        """
        # If the user passes a short name, we map it, otherwise we use the string as is
        self.hf_model_name = self.MODEL_MAP.get(model_name, "unitary/toxic-bert")
        self.model_alias = model_name
        
        # Transformers pipeline uses int id for device (-1 is CPU, 0 is GPU)
        self.device_id = 0 if device == "cuda" else -1
        self._pipeline = None

    def _load_model(self):
        """Lazy load the pipeline."""
        if self._pipeline is None:
            try:
                from transformers import pipeline
                
                print(f"Loading Toxicity model directly: {self.hf_model_name}...")
                
                # return_all_scores=True (or top_k=None in newer versions) is vital 
                # to obtain all the labels (toxic, severe_toxic, etc.)
                self._pipeline = pipeline(
                    "text-classification",
                    model=self.hf_model_name,
                    device=self.device_id,
                    top_k=None,  # This ensures that we return all the labels
                    truncation=True,
                    max_length=512,
                )
                print(f"Loaded Toxicity model successfully.")
            except Exception as e:
                print(f"Failed to load Toxicity model: {e}")
                # Important: Do not raise the exception to allow the fallback in runtime
                # raise e 

    def detect(self, text: str) -> float:
        """
        Detect toxicity in text.
        """
        self._load_model()
        
        if self._pipeline is None:
            return 0.0
        
        try:
            # The pipeline returns a list of lists: [[{'label': 'toxic', 'score': 0.9}, ...]]
            results = self._pipeline(text)
            
            # Flatten the result if necessary
            if isinstance(results, list) and isinstance(results[0], list):
                scores_list = results[0]
            else:
                scores_list = results

            # Convert to a easy to read dictionary: {'toxic': 0.9, 'insult': 0.1, ...}
            scores_dict = {item['label']: item['score'] for item in scores_list}
            
            # Scoring logic (Replica the original logic from your file)
            if "multilingual" in self.model_alias or "unbiased" in self.model_alias:
                # These models usually return a general 'toxicity' label
                return float(scores_dict.get("toxicity", 0.0))
            else:
                # The 'original' (bert) model returns specific labels
                toxic = float(scores_dict.get("toxic", 0.0))
                severe_toxic = float(scores_dict.get("severe_toxic", 0.0))
                
                # Your original weighting logic
                toxicity_score = max(toxic, severe_toxic * 1.2)
            
            return min(max(toxicity_score, 0.0), 1.0)
            
        except Exception as e:
            print(f"Error during Toxicity detection: {e}. Using fallback.")
            return 0.0