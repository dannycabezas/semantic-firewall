"""Fast ML Filter service - core business logic."""

import time
from dataclasses import dataclass
from typing import Any, Dict

from fast_ml_filter.ports.heuristic_detector_port import IHeuristicDetector
from fast_ml_filter.ports.pii_detector_port import IPIIDetector
from fast_ml_filter.ports.prompt_injection_detector_port import IPromptInjectionDetector
from fast_ml_filter.ports.toxicity_detector_port import IToxicityDetector


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

    def analyze(self, text: str) -> MLSignals:
        """
        Analyze text with all detectors.

        Args:
            text: Text to analyze

        Returns:
            MLSignals with all detection results
        """
        start_time = time.time()

        # Run all detectors
        pii_score = self.pii_detector.detect(text)
        toxicity_score = self.toxicity_detector.detect(text)
        prompt_injection_score = self.prompt_injection_detector.detect(text)
        heuristic_result = self.heuristic_detector.detect(text)

        latency_ms = (time.time() - start_time) * 1000

        return MLSignals(
            pii_score=pii_score,
            toxicity_score=toxicity_score,
            prompt_injection_score=prompt_injection_score,
            heuristic_flags=heuristic_result.get("flags", []),
            heuristic_blocked=heuristic_result.get("blocked", False),
            heuristic_reason=heuristic_result.get("reason"),
            latency_ms=latency_ms,
        )
