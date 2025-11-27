"""Factory for creating detector instances dynamically."""

import logging
import threading
from typing import Any, Dict, Optional
from config import FirewallConfig
from fast_ml_filter.ports.pii_detector_port import IPIIDetector
from fast_ml_filter.ports.toxicity_detector_port import IToxicityDetector
from fast_ml_filter.ports.prompt_injection_detector_port import IPromptInjectionDetector
from fast_ml_filter.ports.heuristic_detector_port import IHeuristicDetector
from fast_ml_filter.adapters.custom_onnx_prompt_injection_detector import CustomONNXPromptInjectionDetector
from fast_ml_filter.adapters.deberta_prompt_injection_detector import DeBERTaPromptInjectionDetector
from fast_ml_filter.adapters.llama_prompt_guard_detector import LlamaPromptGuardDetector
from fast_ml_filter.adapters.presidio_pii_detector import PresidioPIIDetector
from fast_ml_filter.adapters.onnx_pii_detector import ONNXPIIDetector
from fast_ml_filter.adapters.mock_pii_detector import MockPIIDetector
from fast_ml_filter.adapters.detoxify_toxicity_detector import DetoxifyToxicityDetector
from fast_ml_filter.adapters.onnx_toxicity_detector import ONNXToxicityDetector
from fast_ml_filter.adapters.regex_heuristic_detector import RegexHeuristicDetector


class DetectorFactory:
    """
    Factory for creating detector instances based on model names.
    
    This is a singleton class with shared cache across all instances to prevent
    reloading models when multiple factories are created.
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    # Shared cache across all instances (class-level)
    _shared_detector_cache: Dict[str, Any] = {}
    
    # Registry of available detectors by category
    PROMPT_INJECTION_DETECTORS: Dict[str, type] = {
        "custom_onnx": CustomONNXPromptInjectionDetector,
        "deberta": DeBERTaPromptInjectionDetector,
        "llama_guard_86m": LlamaPromptGuardDetector,
        "llama_guard_22m": LlamaPromptGuardDetector,
    }
    
    PII_DETECTORS: Dict[str, type] = {
        "presidio": PresidioPIIDetector,
        "onnx": ONNXPIIDetector,
        "mock": MockPIIDetector,
    }
    
    TOXICITY_DETECTORS: Dict[str, type] = {
        "detoxify": DetoxifyToxicityDetector,
        "onnx": ONNXToxicityDetector,
    }
    
    # Default model names
    DEFAULT_PROMPT_INJECTION = "custom_onnx"
    DEFAULT_PII = "presidio"
    DEFAULT_TOXICITY = "onnx"
    
    def __init__(self, config: Optional[FirewallConfig] = None):
        """
        Initialize factory with configuration.
        
        Args:
            config: Firewall configuration (uses default if not provided)
        """
        self.config = config or FirewallConfig()
        
        # Use shared cache at class level
        self._detector_cache = DetectorFactory._shared_detector_cache
        self._cache_logger = logging.getLogger(f"{__name__}.cache")
    
    def create_prompt_injection_detector(
        self, 
        model_name: Optional[str] = None
    ) -> IPromptInjectionDetector:
        """
        Create a prompt injection detector instance with caching.
        
        Args:
            model_name: Name of the model to use (default: "custom_onnx")
            
        Returns:
            IPromptInjectionDetector instance (cached if previously created)
            
        Raises:
            ValueError: If model_name is not recognized
        """
        model_name = model_name or self.DEFAULT_PROMPT_INJECTION
        
        # Check cache first
        cache_key = f"pi_{model_name}"
        if cache_key in self._detector_cache:
            self._cache_logger.info(f"✓ Cache HIT: {cache_key}")
            return self._detector_cache[cache_key]
        
        self._cache_logger.info(f"⚠ Cache MISS: Creating {cache_key}")
        
        if model_name not in self.PROMPT_INJECTION_DETECTORS:
            raise ValueError(
                f"Unknown prompt injection model: {model_name}. "
                f"Available: {list(self.PROMPT_INJECTION_DETECTORS.keys())}"
            )
        
        detector_class = self.PROMPT_INJECTION_DETECTORS[model_name]
        
        # Create instance with appropriate parameters
        if model_name == "custom_onnx":
            detector = detector_class(
                model_path=self.config.ml.prompt_injection_model,
                ollama_base_url=self.config.ml.ollama_base_url,
                ollama_model=self.config.ml.ollama_model,
                threshold=self.config.ml.prompt_injection_threshold,
            )
        elif model_name == "deberta":
            detector = detector_class(
                model_name="ProtectAI/deberta-v3-base-prompt-injection-v2"
            )
        elif model_name == "llama_guard_86m":
            detector = detector_class(
                model_name="meta-llama/Llama-Prompt-Guard-2-86M"
            )
        elif model_name == "llama_guard_22m":
            detector = detector_class(
                model_name="meta-llama/Llama-Prompt-Guard-2-22M"
            )
        else:
            detector = detector_class()
        
        # Cache the detector instance
        self._detector_cache[cache_key] = detector
        self._cache_logger.info(f"✓ Cached: {cache_key}")
        
        return detector
    
    def create_pii_detector(self, model_name: Optional[str] = None) -> IPIIDetector:
        """
        Create a PII detector instance with caching.
        
        Args:
            model_name: Name of the model to use (default: "presidio")
            
        Returns:
            IPIIDetector instance (cached if previously created)
            
        Raises:
            ValueError: If model_name is not recognized
        """
        model_name = model_name or self.DEFAULT_PII
        
        # Check cache first
        cache_key = f"pii_{model_name}"
        if cache_key in self._detector_cache:
            self._cache_logger.info(f"✓ Cache HIT: {cache_key}")
            return self._detector_cache[cache_key]
        
        self._cache_logger.info(f"⚠ Cache MISS: Creating {cache_key}")
        
        if model_name not in self.PII_DETECTORS:
            raise ValueError(
                f"Unknown PII model: {model_name}. "
                f"Available: {list(self.PII_DETECTORS.keys())}"
            )
        
        detector_class = self.PII_DETECTORS[model_name]
        
        # Create instance with appropriate parameters
        if model_name == "onnx":
            detector = detector_class(model_path=self.config.ml.pii_model)
        elif model_name == "mock":
            detector = detector_class(fixed_score=0.0)
        else:  # presidio
            detector = detector_class()
        
        # Cache the detector instance
        self._detector_cache[cache_key] = detector
        self._cache_logger.info(f"✓ Cached: {cache_key}")
        
        return detector
    
    def create_toxicity_detector(
        self, 
        model_name: Optional[str] = None
    ) -> IToxicityDetector:
        """
        Create a toxicity detector instance with caching.
        
        Args:
            model_name: Name of the model to use (default: "detoxify")
            
        Returns:
            IToxicityDetector instance (cached if previously created)
            
        Raises:
            ValueError: If model_name is not recognized
        """
        model_name = model_name or self.DEFAULT_TOXICITY
        
        # Check cache first
        cache_key = f"toxicity_{model_name}"
        if cache_key in self._detector_cache:
            self._cache_logger.info(f"✓ Cache HIT: {cache_key}")
            return self._detector_cache[cache_key]
        
        self._cache_logger.info(f"⚠ Cache MISS: Creating {cache_key}")
        
        if model_name not in self.TOXICITY_DETECTORS:
            raise ValueError(
                f"Unknown toxicity model: {model_name}. "
                f"Available: {list(self.TOXICITY_DETECTORS.keys())}"
            )
        
        detector_class = self.TOXICITY_DETECTORS[model_name]
        
        # Create instance with appropriate parameters
        if model_name == "detoxify":
            detector = detector_class(model_name=self.config.ml.detoxify_model_name)
        elif model_name == "onnx":
            detector = detector_class(
                model_path=self.config.ml.toxicity_model,
                tokenizer_path=self.config.ml.toxicity_tokenizer
            )
        else:
            detector = detector_class()
        
        # Cache the detector instance
        self._detector_cache[cache_key] = detector
        self._cache_logger.info(f"✓ Cached: {cache_key}")
        
        return detector
    
    def create_heuristic_detector(self) -> IHeuristicDetector:
        """
        Create a heuristic detector instance.
        
        Returns:
            IHeuristicDetector instance
        """
        return RegexHeuristicDetector(rules_path=self.config.heuristic.rules_path)
    
    @classmethod
    def get_available_models(cls) -> Dict[str, list]:
        """
        Get list of available models for each category.
        
        Returns:
            Dictionary with available models per category
        """
        return {
            "prompt_injection": list(cls.PROMPT_INJECTION_DETECTORS.keys()),
            "pii": list(cls.PII_DETECTORS.keys()),
            "toxicity": list(cls.TOXICITY_DETECTORS.keys()),
        }
    
    @classmethod
    def get_default_models(cls) -> Dict[str, str]:
        """
        Get default model names for each category.
        
        Returns:
            Dictionary with default model names
        """
        return {
            "prompt_injection": cls.DEFAULT_PROMPT_INJECTION,
            "pii": cls.DEFAULT_PII,
            "toxicity": cls.DEFAULT_TOXICITY,
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the detector cache.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "cached_detectors": list(self._detector_cache.keys()),
            "cache_size": len(self._detector_cache),
            "cache_enabled": True
        }
    
    def clear_cache(self) -> int:
        """
        Clear the detector cache.
        
        Returns:
            Number of detectors removed from cache
        """
        count = len(self._detector_cache)
        self._detector_cache.clear()
        self._cache_logger.info(f"Cache cleared: {count} detectors removed")
        return count

