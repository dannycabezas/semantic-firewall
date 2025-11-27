"""Llama Prompt Guard 2 detector adapter for prompt injection and jailbreak detection."""

from fast_ml_filter.ports.prompt_injection_detector_port import IPromptInjectionDetector
from core.request_context import RequestContext
from core.utils.decorators import log_execution_time


class LlamaPromptGuardDetector(IPromptInjectionDetector):
    """
    Llama Prompt Guard 2 implementation for prompt injection and jailbreak detection.
    
    Supports both 86M and 22M parameter versions from Meta.
    Detects three categories: BENIGN, INJECTION, and JAILBREAK.
    
    Model details:
    - 86M: meta-llama/Llama-Prompt-Guard-2-86M (multilingual, higher accuracy)
    - 22M: meta-llama/Llama-Prompt-Guard-2-22M (faster, good accuracy)
    """

    def __init__(
        self, 
        model_name: str = "meta-llama/Llama-Prompt-Guard-2-86M"
    ) -> None:
        """
        Initialize Llama Prompt Guard detector.

        Args:
            model_name: HuggingFace model identifier
                       - "meta-llama/Llama-Prompt-Guard-2-86M" (default)
                       - "meta-llama/Llama-Prompt-Guard-2-22M"
        """
        self.model_name = model_name
        self._classifier = None
        self._use_model = False

    @log_execution_time()
    def _load_model(self) -> None:
        """Lazy load Llama Prompt Guard model with pipeline."""
        if not self._use_model:
            try:
                import torch
                from transformers import pipeline
                from os import getenv

                hf_token = getenv("HF_TOKEN")
                if not hf_token:
                    print("HF_TOKEN not found in environment variables. Using fallback.")

                # Use GPU if available, otherwise CPU
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                
                # Create pipeline for text classification
                # Llama Prompt Guard 2 supports up to 512 tokens
                self._classifier = pipeline(
                    "text-classification",
                    model=self.model_name,
                    truncation=True,
                    max_length=512,
                    device=device,
                    token=hf_token,
                )

                self._use_model = True
                print(
                    f"Loaded Llama Prompt Guard model: {self.model_name} on {device}"
                )
            except Exception as e:
                print(f"Failed to load Llama Prompt Guard model: {e}. Using fallback.")
                self._use_model = False

    def _map_label_to_score(self, label: str, confidence: float) -> float:
        """
        Map model output label and confidence to injection score.
        
        Labels:
        - BENIGN: Safe prompt, no injection detected
        - INJECTION: Prompt injection attempt detected
        - JAILBREAK: Jailbreak attempt detected (e.g., DAN prompts)
        
        Args:
            label: Classification label from model
            confidence: Model confidence score (0.0 to 1.0)
            
        Returns:
            Injection score between 0.0 and 1.0
        """
        label_upper = label.upper()
        
        if label_upper == "LABEL_0":
            # Benign prompt: low injection score
            # Invert confidence: high confidence in benign = low injection score
            return max(0.0, 1.0 - confidence)
        
        elif label_upper == "LABEL_1":
            # Injection detected: high score based on confidence
            # Scale to 0.7-1.0 range
            return 0.7 + (confidence * 0.3)
        
        elif label_upper == "LABEL_2":
            # Jailbreak detected: treat as high-risk injection
            # Scale to 0.7-1.0 range (same as injection per user preference)
            return 0.7 + (confidence * 0.3)
        
        else:
            # Unknown label: use confidence as-is
            return confidence

    @log_execution_time()
    def detect(self, text: str, context: RequestContext | None = None) -> float:
        """
        Detect prompt injection and jailbreak attempts in text.

        Args:
            text: Text to analyze (will be truncated to 512 tokens)
            context: Request context (optional, not used by this detector)
            
        Returns:
            Prompt injection score between 0.0 and 1.0
            - 0.0-0.3: Likely benign
            - 0.3-0.7: Suspicious
            - 0.7-1.0: High confidence injection/jailbreak
        """
        # Load model if not already loaded
        self._load_model()

        if self._use_model and self._classifier:
            try:
                # Run classification
                result = self._classifier(text)
                # result format: [{'label': 'BENIGN'/'INJECTION'/'JAILBREAK', 'score': 0.95}]
                
                if isinstance(result, list) and len(result) > 0:
                    label = result[0].get('label', '')
                    confidence = result[0].get('score', 0.0)
                    
                    # Map label and confidence to injection score
                    injection_score = self._map_label_to_score(label, confidence)
                    return float(injection_score)
                
                # Fallback if unexpected format
                return 0.0

            except Exception as e:
                print(f"Error during Llama Prompt Guard inference: {e}. Using fallback.")

        # Fallback: keyword-based detection
        return self._fallback_detection(text)

    def _fallback_detection(self, text: str) -> float:
        """
        Fallback keyword-based prompt injection detection.

        Args:
            text: Text to analyze

        Returns:
            Injection score based on keyword matches
        """
        injection_keywords = [
            "ignore previous",
            "ignore all previous",
            "forget instructions",
            "disregard instructions",
            "system prompt",
            "override",
            "new instructions",
            "disregard",
            "pretend you are",
            "act as if",
            "you are now",
            "new role",
            "roleplay",
            "forget everything",
            "ignore everything",
            "jailbreak",
            "DAN mode",
            "developer mode",
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

