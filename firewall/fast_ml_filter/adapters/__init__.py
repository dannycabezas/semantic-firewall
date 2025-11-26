"""Adapters (implementations) for fast ML filter module."""

from fast_ml_filter.adapters.mock_pii_detector import MockPIIDetector
from fast_ml_filter.adapters.onnx_pii_detector import ONNXPIIDetector
from fast_ml_filter.adapters.onnx_toxicity_detector import ONNXToxicityDetector
from fast_ml_filter.adapters.regex_heuristic_detector import \
    RegexHeuristicDetector
from fast_ml_filter.adapters.detoxify_toxicity_detector import DetoxifyToxicityDetector
from fast_ml_filter.adapters.custom_onnx_prompt_injection_detector import \
    CustomONNXPromptInjectionDetector
from fast_ml_filter.adapters.deberta_prompt_injection_detector import \
    DeBERTaPromptInjectionDetector
from fast_ml_filter.adapters.llama_prompt_guard_detector import \
    LlamaPromptGuardDetector
from fast_ml_filter.adapters.presidio_pii_detector import PresidioPIIDetector

__all__ = [
    "ONNXPIIDetector",
    "ONNXToxicityDetector",
    "RegexHeuristicDetector",
    "MockPIIDetector",
    "PresidioPIIDetector",
    "DetoxifyToxicityDetector",
    "CustomONNXPromptInjectionDetector",
    "DeBERTaPromptInjectionDetector",
    "LlamaPromptGuardDetector",
]
