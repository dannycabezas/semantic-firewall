"""Memory-based tenant context provider adapter (mock for POC)."""

from typing import Dict, Any
from policy_engine.ports.tenant_context_port import ITenantContextProvider


class MemoryTenantContext(ITenantContextProvider):
    """In-memory tenant context provider (mock for POC)."""

    def __init__(self):
        """Initialize tenant context store."""
        self._contexts: Dict[str, Dict[str, Any]] = {
            "default": {
                "allow_pii": False,
                "toxicity_threshold": 0.7,
                "pii_threshold": 0.8,
                "max_length": 4000,
            }
        }

    def get_context(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get context for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary with tenant context
        """
        return self._contexts.get(tenant_id, self._contexts["default"])

