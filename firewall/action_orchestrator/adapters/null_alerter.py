"""Null alerter adapter (no-op for POC)."""

from typing import Any, Dict

from action_orchestrator.ports.alerter_port import IAlerter


class NullAlerter(IAlerter):
    """Null implementation for alerting (no-op)."""

    def alert(self, severity: str, message: str, context: Dict[str, Any] = None) -> bool:
        """
        Send an alert (no-op).

        Args:
            severity: Alert severity
            message: Alert message
            context: Additional context

        Returns:
            True (always succeeds, but does nothing)
        """
        return True
