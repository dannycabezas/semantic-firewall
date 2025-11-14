class FirewallException(Exception):
    """Base exception for firewall errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class BackendError(FirewallException):
    """Error communicating with the backend."""

    pass


class ContentBlockedException(FirewallException):
    """Exception raised when content is blocked by the firewall."""

    def __init__(
        self,
        reason: str,
        direction: str = "ingress",
        details: dict | None = None,
    ) -> None:
        super().__init__(f"Content blocked ({direction}): {reason}")
        self.reason = reason
        self.direction = direction
        self.details = details or {}
        self.ml_signals = None  # To attach ML signals
        self.preprocessed = None  # To attach preprocessed data
