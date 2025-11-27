"""Fast ML Filter service - core business logic."""

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from core.request_context import RequestContext
from fast_ml_filter.detector_factory import DetectorFactory
from fast_ml_filter.ports.heuristic_detector_port import IHeuristicDetector
from fast_ml_filter.ports.pii_detector_port import IPIIDetector
from fast_ml_filter.ports.prompt_injection_detector_port import IPromptInjectionDetector
from fast_ml_filter.ports.toxicity_detector_port import IToxicityDetector


@dataclass
class DetectorMetrics:
    """Métricas de un detector individual."""
    score: float
    latency_ms: float


@dataclass
class MLSignals:
    """Data structure for ML detection signals."""

    pii_score: float
    toxicity_score: float
    prompt_injection_score: float
    heuristic_flags: list
    heuristic_blocked: bool
    heuristic_reason: str
    latency_ms: float
    # Nuevas métricas individuales
    pii_metrics: DetectorMetrics = None
    toxicity_metrics: DetectorMetrics = None
    prompt_injection_metrics: DetectorMetrics = None
    heuristic_metrics: DetectorMetrics = None


class MLFilterService:
    """Service for fast ML-based filtering."""

    def __init__(
        self,
        pii_detector: IPIIDetector,
        toxicity_detector: IToxicityDetector,
        prompt_injection_detector: IPromptInjectionDetector,
        heuristic_detector: IHeuristicDetector,
    ):
        """
        Initialize ML filter service with injected dependencies.

        Args:
            pii_detector: PII detector implementation
            toxicity_detector: Toxicity detector implementation
            heuristic_detector: Heuristic detector implementation
        """
        self.pii_detector = pii_detector
        self.toxicity_detector = toxicity_detector
        self.prompt_injection_detector = prompt_injection_detector
        self.heuristic_detector = heuristic_detector

    @classmethod
    def create_with_models(
        cls,
        model_config: Optional[Dict[str, str]] = None,
        factory: Optional[DetectorFactory] = None
    ) -> "MLFilterService":
        """
        Factory method to create MLFilterService with specific detector models.
        
        Args:
            model_config: Dictionary with model names for each category:
                - "prompt_injection": model name (e.g., "custom_onnx", "deberta")
                - "pii": model name (e.g., "presidio", "onnx", "mock")
                - "toxicity": model name (e.g., "detoxify", "onnx")
            factory: DetectorFactory instance (creates new one if not provided)
            
        Returns:
            MLFilterService instance with specified detectors
        """
        if factory is None:
            factory = DetectorFactory()
        
        # Extract model names from config or use defaults
        if model_config is None:
            model_config = {}
        
        prompt_injection_model = model_config.get("prompt_injection")
        pii_model = model_config.get("pii")
        toxicity_model = model_config.get("toxicity")
        
        # Create detectors
        pii_detector = factory.create_pii_detector(pii_model)
        toxicity_detector = factory.create_toxicity_detector(toxicity_model)
        prompt_injection_detector = factory.create_prompt_injection_detector(prompt_injection_model)
        heuristic_detector = factory.create_heuristic_detector()
        
        return cls(
            pii_detector=pii_detector,
            toxicity_detector=toxicity_detector,
            prompt_injection_detector=prompt_injection_detector,
            heuristic_detector=heuristic_detector,
        )

    async def analyze(self, text: str, context: RequestContext | None = None) -> MLSignals:
        """
        Analyze text with all detectors in parallel.

        Args:
            text: Text to analyze
            context: Request context
        Returns:
            MLSignals with all detection results
        """
        start_time = time.time()

        # Run all detectors in parallel using asyncio.to_thread
        async def run_pii() -> Tuple[float, float]:
            detector_start = time.time()
            score = await asyncio.to_thread(self.pii_detector.detect, text)
            latency = (time.time() - detector_start) * 1000
            return score, latency

        async def run_toxicity() -> Tuple[float, float]:
            detector_start = time.time()
            score = await asyncio.to_thread(self.toxicity_detector.detect, text)
            latency = (time.time() - detector_start) * 1000
            return score, latency

        async def run_prompt_injection() -> Tuple[float, float]:
            detector_start = time.time()
            score = await asyncio.to_thread(
                self.prompt_injection_detector.detect, text, context
            )
            latency = (time.time() - detector_start) * 1000
            return score, latency

        async def run_heuristic() -> Tuple[Dict, float]:
            detector_start = time.time()
            result = await asyncio.to_thread(self.heuristic_detector.detect, text)
            latency = (time.time() - detector_start) * 1000
            return result, latency

        # Execute all detectors in parallel
        results = await asyncio.gather(
            run_pii(),
            run_toxicity(),
            run_prompt_injection(),
            run_heuristic()
        )

        (pii_score, pii_latency), (toxicity_score, toxicity_latency), \
        (prompt_injection_score, prompt_injection_latency), \
        (heuristic_result, heuristic_latency) = results

        latency_ms = (time.time() - start_time) * 1000

        return MLSignals(
            pii_score=pii_score,
            toxicity_score=toxicity_score,
            prompt_injection_score=prompt_injection_score,
            heuristic_flags=heuristic_result.get("flags", []),
            heuristic_blocked=heuristic_result.get("blocked", False),
            heuristic_reason=heuristic_result.get("reason"),
            latency_ms=latency_ms,
            # Individual metrics
            pii_metrics=DetectorMetrics(score=pii_score, latency_ms=pii_latency),
            toxicity_metrics=DetectorMetrics(score=toxicity_score, latency_ms=toxicity_latency),
            prompt_injection_metrics=DetectorMetrics(score=prompt_injection_score, latency_ms=prompt_injection_latency),
            heuristic_metrics=DetectorMetrics(score=1.0 if heuristic_result.get("blocked") else 0.0, latency_ms=heuristic_latency),
        )
