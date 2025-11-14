from fast_ml_filter.ports.prompt_injection_detector_port import \
    IPromptInjectionDetector


class DeBERTaPromptInjectionDetector(IPromptInjectionDetector):
    """DeBERTa implementation for prompt injection detection using protectai/deberta-v3-base-prompt-injection-v2."""

    def __init__(
        self, model_name: str = "ProtectAI/deberta-v3-base-prompt-injection-v2"
    ) -> None:
        """
        Initialize DeBERTa prompt injection detector.

        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self._classifier = None
        self._use_model = False

    def _load_model(self) -> None:
        """Lazy load DeBERTa model with pipeline."""
        if not self._use_model:
            try:
                import torch
                from transformers import (AutoModelForSequenceClassification,
                                          AutoTokenizer, pipeline)

                # Load tokenizer and model
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name
                )
                
                # Use GPU if available, otherwise CPU
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                
                # Create pipeline
                self._classifier = pipeline(
                    "text-classification",
                    model=model,
                    tokenizer=tokenizer,
                    truncation=True,
                    max_length=512,
                    device=device,
                )

                self._use_model = True
                print(
                    f"Loaded DeBERTa prompt injection model: {self.model_name} on {device}"
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

        if self._use_model and self._classifier:
            try:
                result = self._classifier(text)
                # result format: [{'label': 'INJECTION' or 'SAFE', 'score': 0.95}]
                
                # Look for INJECTION label score
                for item in result:
                    label = item.get('label', '').upper()
                    if 'INJECTION' in label:
                        return float(item['score'])
                    elif 'SAFE' in label:
                        # If SAFE, return inverse (1 - score means injection probability)
                        return 1.0 - float(item['score'])
                
                # Fallback: use first score
                return float(result[0]['score'])

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