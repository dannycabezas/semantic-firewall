"""Rego-based policy loader adapter."""

import os
from typing import Any, Dict

from policy_engine.ports.policy_loader_port import IPolicyLoader


class RegoPolicyLoader(IPolicyLoader):
    """Rego implementation for policy loading."""

    def __init__(self, policies_path: str = "policy_engine/policies.rego"):
        """
        Initialize Rego policy loader.

        Args:
            policies_path: Path to policies Rego file
        """
        self.policies_path = policies_path

    def load(self) -> Dict[str, Any]:
        """
        Load policies from Rego file.

        Returns:
            Dictionary with policy content (raw Rego string)
        """
        try:
            # Try relative to firewall directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            full_path = os.path.join(base_dir, self.policies_path)

            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    return {"rego_policy": f.read(), "path": full_path}
        except Exception as e:
            raise RuntimeError(
                f"Failed to load Rego policy from {self.policies_path}: {e}"
            ) from e

        raise FileNotFoundError(f"Rego policy file not found: {self.policies_path}")
