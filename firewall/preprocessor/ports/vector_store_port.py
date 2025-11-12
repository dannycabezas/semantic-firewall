"""Port for vector storage."""

from abc import ABC, abstractmethod
from typing import List, Optional


class IVectorStore(ABC):
    """Interface for vector storage (Qdrant, Pinecone, etc.)."""

    @abstractmethod
    def store(self, vector_id: str, vector: List[float], metadata: Optional[dict] = None) -> bool:
        """
        Store a vector with optional metadata.
        
        Args:
            vector_id: Unique identifier for the vector
            vector: Embedding vector
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 10) -> List[dict]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of similar vectors with metadata
        """
        pass

