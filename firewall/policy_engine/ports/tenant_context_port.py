"""Port for tenant context provider."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ITenantContextProvider(ABC):
    """Interface for providing tenant context."""

    @abstractmethod
    def get_context(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get context for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary with tenant context (policies, settings, etc.)
        """
        pass

