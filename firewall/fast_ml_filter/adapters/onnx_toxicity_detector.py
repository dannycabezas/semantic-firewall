"""ONNX-based toxicity detector adapter."""

import numpy as np

from fast_ml_filter.ports.toxicity_detector_port import IToxicityDetector


class ONNXToxicityDetector(IToxicityDetector):
    """ONNX implementation for toxicity detection."""

    def __init__(self, model_path: str = None, tokenizer_path: str = None):
        """
        Initialize ONNX toxicity detector.

        Args:
            model_path: Path to ONNX model file
            tokenizer_path: Path to tokenizer (optional, uses transformers if available)
        """
        self.model_path = model_path
        self.tokenizer_path = tokenizer_path
        self._model = None
        self._tokenizer = None
        self._use_model = False

    def _load_model(self):
        """Lazy load ONNX model and tokenizer."""
        if self.model_path and not self._use_model:
            try:
                import onnxruntime as ort
                from transformers import AutoTokenizer

                # Load ONNX model
                self._model = ort.InferenceSession(
                    self.model_path, providers=["CPUExecutionProvider"]  # o 'CUDAExecutionProvider' si tienes GPU
                )

                # Load tokenizer (si tienes el path, úsalo; si no, intenta cargar desde HuggingFace)
                if self.tokenizer_path:
                    self._tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_path)
                else:
                    # Intentar cargar el tokenizer del modelo original
                    try:
                        self._tokenizer = AutoTokenizer.from_pretrained("unitary/toxic-bert")
                    except:
                        # Fallback: usar tokenizer básico
                        from transformers import BertTokenizer

                        self._tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

                self._use_model = True
                print(f"✅ Loaded ONNX toxicity model from {self.model_path}")
            except Exception as e:
                print(f"⚠️ Failed to load ONNX model: {e}. Using fallback.")
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

        if self._use_model and self._model and self._tokenizer:
            try:
                # Tokenize input
                inputs = self._tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=512)

                # Run inference
                outputs = self._model.run(
                    None,
                    {
                        "input_ids": inputs["input_ids"].astype(np.int64),
                        "attention_mask": inputs["attention_mask"].astype(np.int64),
                    },
                )

                # Get logits
                logits = outputs[0]

                # Apply softmax to get probabilities
                import scipy.special

                probs = scipy.special.softmax(logits, axis=-1)

                # Return toxicity probability (assuming binary classification or multi-class)
                # Ajusta según la estructura de tu modelo
                if probs.shape[1] > 1:
                    # Multi-class: suma de probabilidades de clases tóxicas
                    toxicity_score = float(np.sum(probs[0, 1:]))  # Asumiendo clase 0 = no tóxico
                else:
                    # Binary: probabilidad de clase tóxica
                    toxicity_score = float(probs[0, 1] if probs.shape[1] > 1 else probs[0, 0])

                return min(toxicity_score, 1.0)

            except Exception as e:
                print(f"⚠️ Error during ONNX inference: {e}. Using fallback.")

        # Fallback: keyword-based detection
        toxic_keywords = ["hate", "kill", "violence", "attack", "harm", "stupid", "idiot", "moron", "damn", "hell"]

        text_lower = text.lower()
        matches = sum(1 for keyword in toxic_keywords if keyword in text_lower)

        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.3
        elif matches == 2:
            return 0.6
        else:
            return min(0.9, 0.3 + (matches - 1) * 0.2)
