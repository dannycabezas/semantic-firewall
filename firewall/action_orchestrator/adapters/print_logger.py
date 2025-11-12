"""Simple print logger adapter."""

from typing import Dict, Any
from action_orchestrator.ports.logger_port import ILogger


class PrintLogger(ILogger):
    """Simple print-based logger implementation."""

    def log(self, level: str, message: str, **kwargs) -> None:
        """
        Log a message.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context
        """
        print(f"[{level.upper()}] {message}", flush=True)
        if kwargs:
            print(f"  Context: {kwargs}", flush=True)

    def log_structured(self, data: Dict[str, Any]) -> None:
        """
        Log structured data.
        
        Args:
            data: Dictionary of structured data
        """
        import json
        print(f"[STRUCTURED] {json.dumps(data)}", flush=True)

