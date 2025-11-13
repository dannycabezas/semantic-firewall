"""Text normalizer adapter."""

import re

from preprocessor.ports.normalizer_port import INormalizer


class TextNormalizer(INormalizer):
    """Basic text normalizer implementation."""

    def normalize(self, text: str) -> str:
        """
        Normalize text: lowercase, trim, remove extra whitespace.

        Args:
            text: Raw text input

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Convert to lowercase
        normalized = text.lower()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Trim
        normalized = normalized.strip()

        return normalized
