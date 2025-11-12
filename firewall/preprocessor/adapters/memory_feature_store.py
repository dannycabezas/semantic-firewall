"""Memory-based feature store adapter (mock for POC)."""

from typing import Dict, Any, Optional
from preprocessor.ports.feature_store_port import IFeatureStore


class MemoryFeatureStore(IFeatureStore):
    """In-memory feature store implementation (mock for POC)."""

    def __init__(self):
        """Initialize in-memory feature store."""
        self._store: Dict[str, Dict[str, Any]] = {}

    def store(self, entity_id: str, features: Dict[str, Any]) -> bool:
        """
        Store features for an entity.
        
        Args:
            entity_id: Unique identifier for the entity
            features: Dictionary of features
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._store[entity_id] = features.copy()
            return True
        except Exception:
            return False

    def get(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve features for an entity.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            Dictionary of features or None if not found
        """
        return self._store.get(entity_id)

