"""Port for policy evaluation."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class IPolicyEvaluator(ABC):
    """Interface for policy evaluation."""

    @abstractmethod
    def evaluate(
        self,
        ml_signals: Dict[str, Any],
        features: Dict[str, Any],
        policies: Dict[str, Any],
        tenant_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate policies against signals and features.
        
        Args:
            ml_signals: ML detection signals (PII, toxicity, heuristics)
            features: Extracted features
            policies: Policy rules to evaluate
            tenant_context: Tenant-specific context
            
        Returns:
            Dictionary with decision:
            - blocked: bool
            - reason: str
            - confidence: float
        """
        pass

