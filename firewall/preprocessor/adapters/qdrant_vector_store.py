"""Qdrant vector store adapter."""

from typing import List, Optional

from preprocessor.ports.vector_store_port import IVectorStore


class QdrantVectorStore(IVectorStore):
    """Qdrant implementation for vector storage."""

    def __init__(
        self, url: str = "http://localhost:6333", collection_name: str = "firewall_vectors", enabled: bool = True
    ):
        """
        Initialize Qdrant vector store.

        Args:
            url: Qdrant server URL
            collection_name: Name of the collection
            enabled: Whether to actually store vectors (can be disabled for POC)
        """
        self.url = url
        self.collection_name = collection_name
        self.enabled = enabled
        self._client = None
        self._initialized = False

    def _get_client(self):
        """Lazy load Qdrant client."""
        if self._client is None and self.enabled:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams

                self._client = QdrantClient(url=self.url)

                # Create collection if it doesn't exist
                if not self._initialized:
                    try:
                        self._client.get_collection(self.collection_name)
                    except Exception:
                        # Collection doesn't exist, create it
                        # Default dimension for all-MiniLM-L6-v2
                        self._client.create_collection(
                            collection_name=self.collection_name,
                            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                        )
                    self._initialized = True
            except ImportError:
                # Qdrant not available, use mock mode
                self.enabled = False

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
        if not self.enabled:
            return True  # Mock mode: always succeed

        try:
            self._get_client()
            if self._client:
                from qdrant_client.models import PointStruct

                point = PointStruct(id=vector_id, vector=vector, payload=metadata or {})
                self._client.upsert(collection_name=self.collection_name, points=[point])
                return True
        except Exception:
            pass

        return False

    def search(self, query_vector: List[float], top_k: int = 10) -> List[dict]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of similar vectors with metadata
        """
        if not self.enabled:
            return []  # Mock mode: return empty

        try:
            self._get_client()
            if self._client:
                results = self._client.search(
                    collection_name=self.collection_name, query_vector=query_vector, limit=top_k
                )
                return [{"id": hit.id, "score": hit.score, "metadata": hit.payload} for hit in results]
        except Exception:
            pass

        return []
