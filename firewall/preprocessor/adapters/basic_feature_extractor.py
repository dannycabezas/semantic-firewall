"""Basic feature extractor adapter."""

import re
from typing import Any, Dict

from preprocessor.ports.feature_extractor_port import IFeatureExtractor


class BasicFeatureExtractor(IFeatureExtractor):
    """Basic feature extraction implementation."""

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract basic features from text.

        Args:
            text: Normalized text input

        Returns:
            Dictionary of extracted features
        """
        if not text:
            return {
                "length": 0,
                "word_count": 0,
                "char_count": 0,
                "has_numbers": False,
                "has_special_chars": False,
            }

        # Basic features
        features = {
            "length": len(text),
            "word_count": len(text.split()),
            "char_count": len(text),
            "has_numbers": bool(re.search(r"\d", text)),
            "has_special_chars": bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', text)),
        }

        # Count special patterns
        features["url_count"] = len(
            re.findall(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                text,
            )
        )
        features["email_count"] = len(
            re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        )

        return features
