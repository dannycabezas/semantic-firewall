"""Fast ML Filter service - core business logic."""

import time
from dataclasses import dataclass
from typing import Any, Dict

from fast_ml_filter.ports.heuristic_detector_port import IHeuristicDetector
from fast_ml_filter.ports.pii_detector_port import IPIIDetector
from fast_ml_filter.ports.prompt_injection_detector_port import \
    IPromptInjectionDetector
from fast_ml_filter.ports.toxicity_detector_port import IToxicityDetector
from core.request_context import RequestContext


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

    def analyze(self, text: str, context: RequestContext | None = None) -> MLSignals:
        """
        Analyze text with all detectors.

        Args:
            text: Text to analyze
            context: Request context
        Returns:
            MLSignals with all detection results
        """
        start_time = time.time()

        # Run all detectors with individual metrics
        pii_start = time.time()
        pii_score = self.pii_detector.detect(text)
        pii_latency = (time.time() - pii_start) * 1000
        
        toxicity_start = time.time()
        toxicity_score = self.toxicity_detector.detect(text)
        toxicity_latency = (time.time() - toxicity_start) * 1000
        
        prompt_injection_start = time.time()
        prompt_injection_score = self.prompt_injection_detector.detect(text, context)
        prompt_injection_latency = (time.time() - prompt_injection_start) * 1000
        
        heuristic_start = time.time()
        heuristic_result = self.heuristic_detector.detect(text)
        heuristic_latency = (time.time() - heuristic_start) * 1000

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
