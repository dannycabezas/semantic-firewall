from fast_ml_filter.ports.prompt_injection_detector_port import \
    IPromptInjectionDetector


class DeBERTaPromptInjectionDetector(IPromptInjectionDetector):
    """DeBERTa implementation for prompt injection detection using protectai/deberta-v3-base-prompt-injection."""

    def __init__(
        self, model_name: str = "protectai/deberta-v3-base-prompt-injection"
    ) -> None:
        """
        Initialize DeBERTa prompt injection detector.

        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
        self._use_model = False

    def _load_model(self) -> None:
        """Lazy load DeBERTa model and tokenizer."""
        if not self._use_model:
            try:
                import torch
                from transformers import (AutoModelForSequenceClassification,
                                          AutoTokenizer)

                # Load tokenizer and model
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name
                )
                self._model.eval()  # Set to evaluation mode

                # Use GPU if available, otherwise CPU
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
                self._model = self._model.to(self._device)

                self._use_model = True
                print(
                    f"Loaded DeBERTa prompt injection model: {self.model_name} on {self._device}"
                )
            except Exception as e:
                print(f"Failed to load DeBERTa model: {e}. Using fallback.")
                self._use_model = False

    def detect(self, text: str) -> float:
        """
        Detect prompt injection in text.

        Args:
            text: Text to analyze

        Returns:
            Prompt injection score between 0.0 and 1.0
        """
        # Try to use DeBERTa model if available
        self._load_model()

        if self._use_model and self._model and self._tokenizer:
            try:
                import torch

                # Tokenize input
                inputs = self._tokenizer(
                    text,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=512,
                )
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

                # Run inference
                with torch.no_grad():
                    outputs = self._model(**inputs)
                    logits = outputs.logits

                # Apply softmax to get probabilities
                import torch.nn.functional as F

                probs = F.softmax(logits, dim=-1)

                # The model typically outputs: [no_injection_prob, injection_prob]
                # Return the probability of prompt injection (class 1)
                if probs.shape[1] > 1:
                    injection_score = float(probs[0, 1].item())
                else:
                    # Fallback if single output
                    injection_score = float(probs[0, 0].item())

                return min(injection_score, 1.0)

            except Exception as e:
                print(f"Error during DeBERTa inference: {e}. Using fallback.")

        # Fallback: keyword-based detection
        injection_keywords = [
            "ignore previous",
            "forget instructions",
            "system prompt",
            "override",
            "new instructions",
            "disregard",
            "pretend you are",
            "act as if",
        ]

        text_lower = text.lower()
        matches = sum(1 for keyword in injection_keywords if keyword in text_lower)

        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.3
        elif matches == 2:
            return 0.6
        else:
            return min(0.9, 0.3 + (matches - 1) * 0.2)
