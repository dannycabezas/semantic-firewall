"""Request context for passing metadata through the analysis pipeline."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class RequestContext:
    """Context information for a request being analyzed."""
    
    # Request identification
    request_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow )
    
    # User/Session info
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = "default"
    
    # Request metadata
    endpoint: Optional[str] = None
    device: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    
    # LLM parameters (if applicable)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    turn_count: Optional[int] = None
    
    # Custom metadata
    custom: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for formatting."""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id or "unknown",
            "session_id": self.session_id or "unknown",
            "tenant_id": self.tenant_id,
            "endpoint": self.endpoint or "/threat/query",
            "device": self.device or "Unknown",
            "rate_limit": self.rate_limit_remaining or 0,
            "temperature": self.temperature or 0.5,
            "max_tokens": self.max_tokens or 20,
            "turn_count": self.turn_count or 1,
            **self.custom
        }