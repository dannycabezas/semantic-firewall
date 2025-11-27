"""Llama Prompt Guard 2 detector adapter for prompt injection and jailbreak detection."""

from fast_ml_filter.ports.prompt_injection_detector_port import IPromptInjectionDetector
from core.request_context import RequestContext
from core.utils.decorators import log_execution_time

class LlamaPromptGuardDetector(IPromptInjectionDetector):
    """
    Llama Prompt Guard 2 implementation for prompt injection and jailbreak detection.
    """

    def __init__(
        self, 
        model_name: str = "meta-llama/Llama-Prompt-Guard-2-86M"
    ) -> None:
        self.model_name = model_name
        self._classifier = None
        self._use_model = False

    @log_execution_time()
    def _load_model(self) -> None:
        """Lazy load Llama Prompt Guard model safely handling meta tensors."""
        if not self._use_model:
            try:
                # Imports for lazy loading
                import torch
                from transformers import (
                    pipeline, 
                    AutoModelForSequenceClassification, 
                    AutoTokenizer
                )
                from os import getenv

                hf_token = getenv("HF_TOKEN")
                if not hf_token:
                    print("HF_TOKEN not found in environment variables. Using fallback might fail for gated models.")

                # Device configuration
                device_available = torch.cuda.is_available()
                
                print(f"Loading {self.model_name}...")

                # STEP 1: Load Tokenizer
                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name, 
                    token=hf_token
                )

                # STEP 2: Load Model explicitly
                # We use device_map="auto" if there is GPU, which manages the meta tensors automatically
                # with the library 'accelerate'.
                model_kwargs = {
                    "token": hf_token,
                    "low_cpu_mem_usage": True,  # Key to avoid the meta tensor error
                }
                
                if device_available:
                    model_kwargs["device_map"] = "auto"
                
                model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    **model_kwargs
                )

                # STEP 3: Create Pipeline injecting the already loaded model
                # Note: We do not pass 'device' here because the model is already on the correct device
                self._classifier = pipeline(
                    "text-classification",
                    model=model,
                    tokenizer=tokenizer,
                    truncation=True,
                    max_length=512,
                    # device=device, # DO NOT USE device here if we use device_map in the model
                )

                self._use_model = True
                print(f"Successfully loaded Llama Prompt Guard model.")
                
            except Exception as e:
                print(f"Failed to load Llama Prompt Guard model: {e}. Using fallback.")
                import traceback
                traceback.print_exc() # This will help you see if any libraries are missing
                self._use_model = False

    def _map_label_to_score(self, label: str, confidence: float) -> float:
        """
        Map model output label and confidence to injection score.
        Updated to handle both ID labels (LABEL_0) and String labels (BENIGN).
        """
        label_upper = label.upper()
        
        # Mapping for Llama Prompt Guard 2
        # Sometimes returns the direct names if the config is loaded properly
        is_benign = label_upper in ["LABEL_0", "BENIGN", "SAFE"]
        is_injection = label_upper in ["LABEL_1", "INJECTION"]
        is_jailbreak = label_upper in ["LABEL_2", "JAILBREAK"]
        
        if is_benign:
            return max(0.0, 1.0 - confidence)
        
        elif is_injection:
            return 0.7 + (confidence * 0.3)
        
        elif is_jailbreak:
            return 0.7 + (confidence * 0.3)
        
        else:
            # If the model returns something unexpected, we assume moderate risk
            return confidence

    @log_execution_time()
    def detect(self, text: str, context: RequestContext | None = None) -> float:
        # Load model if not already loaded
        self._load_model()

        if self._use_model and self._classifier:
            try:
                # Run classification
                result = self._classifier(text)
                
                if isinstance(result, list) and len(result) > 0:
                    label = result[0].get('label', '')
                    confidence = result[0].get('score', 0.0)
                    
                    injection_score = self._map_label_to_score(label, confidence)
                    return float(injection_score)
                
                return 0.0

            except Exception as e:
                print(f"Error during Llama Prompt Guard inference: {e}. Using fallback.")

        return self._fallback_detection(text)

    def _fallback_detection(self, text: str) -> float:
        injection_keywords = [
            "ignore previous", "ignore all previous", "forget instructions",
            "disregard instructions", "system prompt", "override",
            "new instructions", "disregard", "pretend you are",
            "act as if", "you are now", "new role",
            "roleplay", "forget everything", "ignore everything",
            "jailbreak", "DAN mode", "developer mode",
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