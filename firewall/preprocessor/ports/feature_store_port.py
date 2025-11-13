"""Port for feature storage."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IFeatureStore(ABC):
    """Interface for feature storage (Feast, dict, etc.)."""

    @abstractmethod
    def store(self, entity_id: str, features: Dict[str, Any]) -> bool:
        """
        Store features for an entity.

        Args:
            entity_id: Unique identifier for the entity
            features: Dictionary of features

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve features for an entity.

        Args:
            entity_id: Unique identifier for the entity

        Returns:
            Dictionary of features or None if not found
        """
        pass
