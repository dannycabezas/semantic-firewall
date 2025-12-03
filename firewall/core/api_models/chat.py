from typing import Optional

from pydantic import BaseModel


class DetectorMetrics(BaseModel):
    """Metrics of an individual detector."""

    name: str
    score: float
    latency_ms: float
    threshold: float | None = None
    status: str = "pass"  # pass, warn, block


class PreprocessingMetrics(BaseModel):
    """Preprocessing phase metrics."""

    original_length: int
    normalized_length: int
    word_count: int
    char_count: int


class PolicyMetrics(BaseModel):
    """Policy evaluation metrics."""

    matched_rule: str | None = None
    confidence: float
    risk_level: str  # low, medium, high, critical


class ChatResponse(BaseModel):
    blocked: bool = False
    reason: str | None = None
    reply: str | None = None
    # Enhanced metrics
    ml_detectors: list[DetectorMetrics] | None = None
    preprocessing: PreprocessingMetrics | None = None
    policy: PolicyMetrics | None = None
    # Latencies breakdown
    latency_breakdown: dict[str, float] | None = None
    total_latency_ms: float | None = None


class ChatRequest(BaseModel):
    message: str
    detector_config: Optional[dict[str, str]] = None



