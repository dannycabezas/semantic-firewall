from typing import Any
from core.request_context import RequestContext
import os

TENANT_ID = os.getenv("TENANT_ID", "default")


class RequestContextBuilder:
    """Build the request context."""
    
    @staticmethod
    def build(
        request_id: str,
        headers: dict[str, Any],
        endpoint: str = "/api/chat"
    ) -> RequestContext:
        """Build a RequestContext from extracted headers."""
        return RequestContext(
            request_id=request_id,
            user_id=headers["user_id"],
            session_id=headers["session_id"],
            tenant_id=TENANT_ID,
            endpoint=endpoint,
            device=headers["device"],
            temperature=headers["temperature"],
            max_tokens=headers["max_tokens"],
            turn_count=headers["turn_count"],
            rate_limit_remaining=headers["rate_limit"],
        )

