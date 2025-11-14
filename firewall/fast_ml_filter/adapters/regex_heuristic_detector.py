"""Regex-based heuristic detector adapter (uses existing rules)."""

import os
import re
from typing import Any, Dict

import yaml
from fast_ml_filter.ports.heuristic_detector_port import IHeuristicDetector


class RegexHeuristicDetector(IHeuristicDetector):
    """Regex-based heuristic detector using existing rules."""

    def __init__(self, rules_path: str = "rules/prompt_injection_rules.yaml"):
        """
        Initialize heuristic detector with rules.

        Args:
            rules_path: Path to rules YAML file
        """
        self.rules_path = rules_path
        self.patterns = []
        self.denylist = []
        self._load_rules()

    def _load_rules(self):
        """Load rules from YAML file."""
        try:
            rules_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                self.rules_path,
            )
            if os.path.exists(rules_file):
                with open(rules_file, "r") as f:
                    rules = yaml.safe_load(f) or {}
                    self.patterns = [
                        re.compile(pat, re.IGNORECASE)
                        for pat in (rules.get("patterns") or [])
                    ]
                    self.denylist = [s.lower() for s in (rules.get("denylist") or [])]
        except Exception:
            # Fallback to empty rules
            self.patterns = []
            self.denylist = []

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect issues using heuristics.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with detection results
        """
        flags = []
        blocked = False
        reason = None

        # Check patterns
        for pattern in self.patterns:
            if pattern.search(text):
                flags.append(f"pattern_match: {pattern.pattern}")
                blocked = True
                reason = f"Pattern match: {pattern.pattern}"
                break

        # Check denylist
        if not blocked:
            text_lower = text.lower()
            for needle in self.denylist:
                if needle in text_lower:
                    flags.append(f"denylist_match: {needle}")
                    blocked = True
                    reason = f"Contains denylisted token: {needle}"
                    break

        return {"blocked": blocked, "flags": flags, "reason": reason}
