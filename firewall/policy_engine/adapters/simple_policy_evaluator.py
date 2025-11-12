"""Simple policy evaluator adapter."""

from typing import Dict, Any
from policy_engine.ports.policy_evaluator_port import IPolicyEvaluator


class SimplePolicyEvaluator(IPolicyEvaluator):
    """Simple Python-based policy evaluator."""

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
            ml_signals: ML detection signals
            features: Extracted features
            policies: Policy rules to evaluate
            tenant_context: Tenant-specific context
            
        Returns:
            Dictionary with decision
        """
        rules = policies.get("rules", [])
        default_action = policies.get("default_action", "allow")
        
        # Merge tenant context into evaluation context
        context = {
            **ml_signals,
            **features,
            **tenant_context
        }
        
        # Evaluate each rule
        for rule in rules:
            condition = rule.get("condition", "")
            action = rule.get("action", "allow")
            reason = rule.get("reason", "Policy rule matched")
            
            if self._evaluate_condition(condition, context):
                return {
                    "blocked": action == "block",
                    "reason": reason,
                    "confidence": 0.9,
                    "matched_rule": rule.get("name")
                }
        
        # Default action
        return {
            "blocked": default_action == "block",
            "reason": None,
            "confidence": 0.5,
            "matched_rule": None
        }

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a condition string against context.
        
        Args:
            condition: Condition string (e.g., "pii_score > 0.8" or "features.length > 4000")
            context: Evaluation context
            
        Returns:
            True if condition is met
        """
        try:
            # Create evaluation context with flattened nested dicts
            eval_context = {}
            for key, value in context.items():
                if isinstance(value, dict):
                    # Flatten nested dicts (e.g., features.length)
                    for nested_key, nested_value in value.items():
                        eval_context[f"{key}.{nested_key}"] = nested_value
                else:
                    eval_context[key] = value
            
            # Replace variable names in condition with their values
            # Sort by length (longest first) to avoid partial replacements
            eval_condition = condition
            for key in sorted(eval_context.keys(), key=len, reverse=True):
                value = eval_context[key]
                # Replace whole word matches only
                import re
                pattern = r'\b' + re.escape(key) + r'\b'
                eval_condition = re.sub(pattern, str(value), eval_condition)
            
            # Evaluate the condition (safe eval with limited context)
            return bool(eval(eval_condition))
        except Exception:
            return False

