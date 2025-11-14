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
    """Content blocked by policies."""

    def __init__(
        self, reason: str, direction: str = "ingress", details: dict | None = None
    ) -> None:
        self.reason = reason
        self.direction = direction
        super().__init__(f"Content blocked ({direction}): {reason}", details)
