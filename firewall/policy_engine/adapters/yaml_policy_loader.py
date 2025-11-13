"""YAML-based policy loader adapter."""

import os
from typing import Any, Dict

import yaml

from policy_engine.ports.policy_loader_port import IPolicyLoader


class YAMLPolicyLoader(IPolicyLoader):
    """YAML implementation for policy loading."""

    def __init__(self, policies_path: str = "policy_engine/policies.yaml"):
        """
        Initialize YAML policy loader.

        Args:
            policies_path: Path to policies YAML file
        """
        self.policies_path = policies_path

    def load(self) -> Dict[str, Any]:
        """
        Load policies from YAML file.

        Returns:
            Dictionary of policy rules
        """
        try:
            # Try relative to firewall directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            full_path = os.path.join(base_dir, self.policies_path)

            if os.path.exists(full_path):
                with open(full_path, "r") as f:
                    return yaml.safe_load(f) or {}
        except Exception:
            pass

        # Return default policies if file not found
        return {
            "rules": [
                {
                    "name": "heuristic_block",
                    "condition": "heuristic_blocked == True",
                    "action": "block",
                    "reason": "Heuristic detection blocked",
                },
                {
                    "name": "pii_threshold",
                    "condition": "pii_score > 0.8",
                    "action": "block",
                    "reason": "High PII score detected",
                },
                {
                    "name": "toxicity_threshold",
                    "condition": "toxicity_score > 0.7",
                    "action": "block",
                    "reason": "High toxicity score detected",
                },
                {
                    "name": "max_length",
                    "condition": "features.length > 4000",
                    "action": "block",
                    "reason": "Prompt too long",
                },
            ],
            "default_action": "allow",
        }
