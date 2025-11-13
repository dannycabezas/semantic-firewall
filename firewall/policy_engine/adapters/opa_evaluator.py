"""OPA-based policy evaluator adapter using HTTP client."""

import logging
from typing import Any, Dict

import httpx

from policy_engine.ports.policy_evaluator_port import IPolicyEvaluator

logger = logging.getLogger(__name__)


class OPAEvaluator(IPolicyEvaluator):
    """OPA-based policy evaluator using Rego via HTTP API."""

    def __init__(self, opa_url: str = "http://localhost:8181", opa_policy_name: str = "firewall/policy"):
        """
        Initialize OPA evaluator.

        Args:
            opa_url: URL of OPA server (default: http://localhost:8181)
            opa_policy_name: Policy name/path in OPA (default: firewall/policy)
        """
        self.opa_url = opa_url.rstrip("/")
        self.opa_policy_name = opa_policy_name
        self.client = httpx.Client(timeout=5.0)
        self._policy_loaded = False
        self._current_policy_hash = None

    def _check_health(self) -> bool:
        """Check if OPA server is healthy."""
        try:
            response = self.client.get(f"{self.opa_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OPA health check failed: {e}")
            return False

    def _load_policy(self, rego_policy: str) -> None:
        """
        Load Rego policy into OPA server.

        Args:
            rego_policy: Rego policy content as string
        """
        import hashlib
        
        # Check if policy has changed
        policy_hash = hashlib.md5(rego_policy.encode()).hexdigest()
        if self._current_policy_hash == policy_hash and self._policy_loaded:
            logger.debug("Policy unchanged, skipping reload")
            return

        try:
            # OPA API: PUT /v1/policies/{policy_name}
            policy_name = self.opa_policy_name.replace("/", ".")
            url = f"{self.opa_url}/v1/policies/{policy_name}"
            
            response = self.client.put(
                url,
                content=rego_policy,
                headers={"Content-Type": "text/plain"},
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Policy '{policy_name}' loaded successfully into OPA")
                self._policy_loaded = True
                self._current_policy_hash = policy_hash
            else:
                error_msg = f"Failed to load policy: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to OPA server: {e}")
            raise RuntimeError(f"OPA server connection failed: {e}") from e

    def _evaluate_policy(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate policy using OPA HTTP API.

        Args:
            input_data: Input data for policy evaluation

        Returns:
            Decision dictionary from OPA
        """
        try:
            # OPA API: POST /v1/data/{policy_path}
            data_path = self.opa_policy_name
            url = f"{self.opa_url}/v1/data/{data_path}/decision"
            
            response = self.client.post(
                url,
                json={"input": input_data},
            )
            
            if response.status_code == 200:
                result = response.json()
                # OPA returns {"result": {...}}
                return result.get("result", {})
            else:
                error_msg = f"OPA evaluation failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        except httpx.RequestError as e:
            logger.error(f"Failed to evaluate policy: {e}")
            raise

    def evaluate(
        self,
        ml_signals: Dict[str, Any],
        features: Dict[str, Any],
        policies: Dict[str, Any],
        tenant_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate policies against signals and features using OPA.

        Args:
            ml_signals: ML detection signals
            features: Extracted features
            policies: Policy rules (Rego content)
            tenant_context: Tenant-specific context

        Returns:
            Dictionary with decision:
            - blocked: bool
            - reason: str
            - confidence: float
            - matched_rule: str
        """
        # Load policy if needed
        rego_policy = policies.get("rego_policy")
        if not rego_policy:
            logger.error("No 'rego_policy' found in policies dictionary")
            return {
                "blocked": False,
                "reason": "Policy evaluation error: No Rego policy found",
                "confidence": 0.0,
                "matched_rule": None,
            }

        # Prepare input for OPA
        input_data = {
            "ml_signals": ml_signals,
            "features": features,
            "tenant_context": tenant_context,
        }

        try:
            # Load policy (only if changed)
            self._load_policy(rego_policy)

            # Evaluate policy
            decision = self._evaluate_policy(input_data)

            if not decision:
                logger.warning("OPA query returned no results, defaulting to allow")
                return {
                    "blocked": False,
                    "reason": None,
                    "confidence": 0.5,
                    "matched_rule": None,
                }

            return {
                "blocked": decision.get("blocked", False),
                "reason": decision.get("reason"),
                "confidence": decision.get("confidence", 0.5),
                "matched_rule": decision.get("matched_rule"),
            }
        except Exception as e:
            logger.error(f"OPA evaluation failed: {e}")
            # Fail open - allow if OPA fails
            return {
                "blocked": False,
                "reason": f"Policy evaluation error: {str(e)}",
                "confidence": 0.0,
                "matched_rule": None,
            }

    def __del__(self):
        """Cleanup HTTP client."""
        if hasattr(self, "client"):
            self.client.close()
