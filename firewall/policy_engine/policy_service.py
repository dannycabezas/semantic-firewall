"""Policy service - core business logic."""

import logging
from dataclasses import dataclass
from typing import Any, Dict

from fast_ml_filter.ml_filter_service import MLSignals
from policy_engine.ports.policy_evaluator_port import IPolicyEvaluator
from policy_engine.ports.policy_loader_port import IPolicyLoader
from policy_engine.ports.tenant_context_port import ITenantContextProvider

logger = logging.getLogger(__name__)


@dataclass
class PolicyDecision:
    """Data structure for policy decision."""

    blocked: bool
    reason: str
    confidence: float
    matched_rule: str = None


class PolicyService:
    """Service for policy evaluation."""

    def __init__(
        self,
        evaluator: IPolicyEvaluator,
        loader: IPolicyLoader,
        tenant_context_provider: ITenantContextProvider,
    ):
        """
        Initialize policy service with injected dependencies.

        Args:
            evaluator: Policy evaluator implementation
            loader: Policy loader implementation
            tenant_context_provider: Tenant context provider implementation
        """
        self.evaluator = evaluator
        self.loader = loader
        self.tenant_context_provider = tenant_context_provider
        self._policies = None

    def _get_policies(self) -> Dict[str, Any]:
        """Lazy load policies."""
        if self._policies is None:
            self._policies = self.loader.load()
        return self._policies

    def evaluate(self, ml_signals: MLSignals, features: Dict[str, Any], tenant_id: str = "default") -> PolicyDecision:
        """
        Evaluate policies and make decision.

        Args:
            ml_signals: ML detection signals
            features: Extracted features
            tenant_id: Tenant identifier

        Returns:
            PolicyDecision with final decision
        """
        # Get policies
        policies = self._get_policies()

        # Get tenant context
        tenant_context = self.tenant_context_provider.get_context(tenant_id)

        # Convert MLSignals to dict for evaluator
        ml_signals_dict = {
            "pii_score": ml_signals.pii_score,
            "toxicity_score": ml_signals.toxicity_score,
            "heuristic_blocked": ml_signals.heuristic_blocked,
            "heuristic_flags": ml_signals.heuristic_flags,
            "heuristic_reason": ml_signals.heuristic_reason,
        }
        logger.info(f"ML signals: {ml_signals_dict}")

        # Evaluate
        result = self.evaluator.evaluate(
            ml_signals=ml_signals_dict, features=features, policies=policies, tenant_context=tenant_context
        )

        return PolicyDecision(
            blocked=result.get("blocked", False),
            reason=result.get("reason"),
            confidence=result.get("confidence", 0.5),
            matched_rule=result.get("matched_rule"),
        )
