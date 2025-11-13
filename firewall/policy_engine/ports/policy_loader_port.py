"""Port for policy loading."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class IPolicyLoader(ABC):
    """Interface for loading policies (YAML, Rego, etc.)."""

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """
        Load policies from source.

        Returns:
            Dictionary of policy rules
        """
        pass
