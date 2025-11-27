"""Preprocessor service - core business logic."""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

from preprocessor.ports.feature_extractor_port import IFeatureExtractor
from preprocessor.ports.feature_store_port import IFeatureStore
from preprocessor.ports.normalizer_port import INormalizer
from preprocessor.ports.vector_store_port import IVectorStore
from preprocessor.ports.vectorizer_port import IVectorizer


@dataclass
class PreprocessedData:
    """Data structure for preprocessed text."""

    original_text: str
    normalized_text: str
    embedding: List[float]
    features: Dict[str, Any]
    vector_id: str


class PreprocessorService:
    """Service for preprocessing and vectorizing text."""

    def __init__(
        self,
        normalizer: INormalizer,
        vectorizer: IVectorizer,
        feature_extractor: IFeatureExtractor,
        vector_store: IVectorStore = None,
        feature_store: IFeatureStore = None,
    ):
        """
        Initialize preprocessor service with injected dependencies.

        Args:
            normalizer: Text normalizer implementation
            vectorizer: Text vectorizer implementation
            feature_extractor: Feature extractor implementation
            vector_store: Optional vector store implementation
            feature_store: Optional feature store implementation
        """
        self.normalizer = normalizer
        self.vectorizer = vectorizer
        self.feature_extractor = feature_extractor
        self.vector_store = vector_store
        self.feature_store = feature_store

    def preprocess(self, text: str, store: bool = True) -> PreprocessedData:
        """
        Preprocess text: normalize, vectorize, extract features.

        Args:
            text: Raw text input
            store: Whether to store vectors and features

        Returns:
            PreprocessedData with all processed information
        """
        # Generate unique ID for this preprocessing
        vector_id = str(uuid.uuid4())

        # 1. Normalize
        normalized_text = self.normalizer.normalize(text)

        # 2. Vectorize
        embedding = [] # self.vectorizer.vectorize(normalized_text)

        # 3. Extract features
        features = self.feature_extractor.extract(normalized_text)

        # 4. Store if enabled
        if store:
            if self.vector_store:
                metadata = {
                    "original_length": len(text),
                    "normalized_length": len(normalized_text),
                    **features,
                }
                self.vector_store.store(vector_id, embedding, metadata)

            if self.feature_store:
                self.feature_store.store(vector_id, features)

        return PreprocessedData(
            original_text=text,
            normalized_text=normalized_text,
            embedding=embedding,
            features=features,
            vector_id=vector_id,
        )
