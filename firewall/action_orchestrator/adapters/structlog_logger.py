"""Structlog logger adapter."""

from typing import Dict, Any
from action_orchestrator.ports.logger_port import ILogger


class StructlogLogger(ILogger):
    """Structlog implementation for logging."""

    def __init__(self):
        """Initialize structlog logger."""
        self._logger = None
        self._use_structlog = False
        self._init_logger()

    def _init_logger(self):
        """Initialize structlog if available."""
        try:
            import structlog
            self._logger = structlog.get_logger()
            self._use_structlog = True
        except ImportError:
            # Fallback to print
            self._use_structlog = False

    def log(self, level: str, message: str, **kwargs) -> None:
        """
        Log a message.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context
        """
        if self._use_structlog and self._logger:
            getattr(self._logger, level)(message, **kwargs)
        else:
            # Fallback to print
            print(f"[{level.upper()}] {message}", flush=True)
            if kwargs:
                print(f"  Context: {kwargs}", flush=True)

    def log_structured(self, data: Dict[str, Any]) -> None:
        """
        Log structured data.
        
        Args:
            data: Dictionary of structured data
        """
        if self._use_structlog and self._logger:
            self._logger.info("structured_log", **data)
        else:
            # Fallback to print
            import json
            print(f"[STRUCTURED] {json.dumps(data)}", flush=True)

