from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from core.exceptions import ContentBlockedException
from fast_ml_filter.ml_filter_service import MLSignals
from policy_engine.policy_service import PolicyDecision
from preprocessor.preprocessor_service import PreprocessedData


class AnalysisDirection(Enum):
    """Direction of the analysis."""

    INGRESS = "ingress"
    EGRESS = "egress"


@dataclass
class AnalysisResult:
    """Result of the analysis of the firewall."""

    preprocessed: PreprocessedData
    ml_signals: MLSignals
    decision: PolicyDecision
    direction: AnalysisDirection
    latency_ms: float = 0.0


class IPreprocessorService(Protocol):
    """Interface of the preprocessing service."""

    def preprocess(self, text: str, store: bool = False) -> PreprocessedData: ...


class IMLFilterService(Protocol):
    """Interface of the ML filter service."""

    def analyze(self, text: str) -> MLSignals: ...


class IPolicyService(Protocol):
    """Interface of the policy service."""

    def evaluate(
        self, ml_signals: MLSignals, features: dict, tenant_id: str
    ) -> PolicyDecision: ...


class FirewallAnalyzer:
    """
    Analysis service of the firewall.

    Responsibility: Analyze content (ingress/egress)
    and determine if it should be blocked.
    """

    def __init__(
        self,
        preprocessor: IPreprocessorService,
        ml_filter: IMLFilterService,
        policy_engine: IPolicyService,
        tenant_id: str = "default",
    ) -> None:
        """
        Initialize the analyzer with the injected dependencies.

        Args:
            preprocessor: Preprocessing service
            ml_filter: ML filter service
            policy_engine: Policy engine
            tenant_id: Tenant ID (default: "default")
        """
        self._preprocessor = preprocessor
        self._ml_filter = ml_filter
        self._policy_engine = policy_engine
        self._tenant_id = tenant_id

    def analyze_content(
        self,
        content: str,
        direction: AnalysisDirection = AnalysisDirection.INGRESS,
        store: bool = False,
    ) -> AnalysisResult:
        """
        Analyze content and return the complete result.

        Args:
            content: Content to analyze
            direction: Analysis direction (ingress/egress)
            store: If it should store the vectors/features

        Returns:
            AnalysisResult with all the information of the analysis

        Raises:
            ContentBlockedException: If the content is blocked
        """
        import time

        start = time.time()

        # 1. Preprocess
        preprocessed = self._preprocessor.preprocess(content, store=store)

        # 2. Analyze with ML
        ml_signals = self._ml_filter.analyze(preprocessed.normalized_text)

        # 3. Evaluate policies
        decision = self._policy_engine.evaluate(
            ml_signals=ml_signals,
            features=preprocessed.features,
            tenant_id=self._tenant_id,
        )

        latency_ms = (time.time() - start) * 1000

        result = AnalysisResult(
            preprocessed=preprocessed,
            ml_signals=ml_signals,
            decision=decision,
            direction=direction,
            latency_ms=latency_ms,
        )

        # Raise exception if blocked
        if decision.blocked:
            exc = ContentBlockedException(
                reason=decision.reason,
                direction=direction.value,
                details={
                    "confidence": decision.confidence,
                    "matched_rule": decision.matched_rule,
                    "latency_ms": latency_ms,
                },
            )
            # Attach ML signals to the exception before raising
            exc.ml_signals = ml_signals
            raise exc

        return result
