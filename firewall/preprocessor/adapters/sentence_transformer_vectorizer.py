"""Sentence transformer vectorizer adapter."""

from typing import List
from preprocessor.ports.vectorizer_port import IVectorizer


class SentenceTransformerVectorizer(IVectorizer):
    """Sentence transformer implementation for vectorization."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize vectorizer with model.
        
        Args:
            model_name: Name of the sentence transformer model
        """
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required. Install with: pip install sentence-transformers"
                )

    def vectorize(self, text: str) -> List[float]:
        """
        Convert text to embedding vector.
        
        Args:
            text: Normalized text input
            
        Returns:
            Embedding vector as list of floats
        """
        if not text:
            # Return zero vector if empty (dimension depends on model)
            return [0.0] * 384  # Default for all-MiniLM-L6-v2
        
        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

