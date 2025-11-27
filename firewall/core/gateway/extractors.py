from fastapi import Request
from typing import Any
from typing import Optional, Dict, Any, Tuple

from fastapi import Request
from core.exceptions import ContentBlockedException
from core.risk import get_risk_level
from core.metrics.adapter import extract_ml_metrics
from core.api_models import (   
    PreprocessingMetrics,
    PolicyMetrics,
)


class HeaderKeys:
    USER_ID = "X-User-ID"
    SESSION_ID = "X-Session-ID"
    USER_AGENT = "User-Agent"
    TEMPERATURE = "X-Temperature"
    MAX_TOKENS = "X-Max-Tokens"
    TURN_COUNT = "X-Turn-Count"
    RATE_LIMIT = "X-Rate-Limit"


class DefaultValues:
    USER_ID = "96424373-aa08-44ae-98ff-9d63e2981663"
    SESSION_ID = "a1e423e8-8486-4309-a660-fdf5b3d55ae9"
    DEVICE = "Unknown"
    TEMPERATURE = 0.5
    MAX_TOKENS = 20
    TURN_COUNT = 1
    RATE_LIMIT = 0


class RequestHeaderExtractor:
    """Extract and validate HTTP request headers."""
    
    @staticmethod
    def extract(request: Request) -> dict[str, Any]:
        """Extract all necessary headers with default values."""
        return {
            "user_id": request.headers.get(HeaderKeys.USER_ID) or DefaultValues.USER_ID,
            "session_id": request.headers.get(HeaderKeys.SESSION_ID) or DefaultValues.SESSION_ID,
            "device": request.headers.get(HeaderKeys.USER_AGENT, DefaultValues.DEVICE),
            "temperature": request.headers.get(HeaderKeys.TEMPERATURE, DefaultValues.TEMPERATURE),
            "max_tokens": request.headers.get(HeaderKeys.MAX_TOKENS, DefaultValues.MAX_TOKENS),
            "turn_count": request.headers.get(HeaderKeys.TURN_COUNT, DefaultValues.TURN_COUNT),
            "rate_limit": request.headers.get(HeaderKeys.RATE_LIMIT, DefaultValues.RATE_LIMIT),
        }




class MetricsExtractor:
    """Extract metrics from the firewall response."""
    
    @staticmethod
    def extract_from_response(
        response: Dict[str, Any],
        detector_config: Optional[Dict] = None
    ) -> Tuple[list, Optional[PreprocessingMetrics], Optional[PolicyMetrics], Dict[str, float]]:
        """
        Extract all metrics from a successful response.
        
        Returns:
            Tuple of (ml_metrics, preprocessing_metrics, policy_metrics, latency_breakdown)
        """
        ml_metrics = []
        preprocessing_metrics = None
        policy_metrics = None
        latency_breakdown = {}
        
        metrics = response.get("metrics", {})
        ml_signals = metrics.get("ml_signals")
        preprocessed = metrics.get("preprocessed")
        decision = metrics.get("decision")
        
        if ml_signals:
            ml_metrics = extract_ml_metrics(ml_signals, detector_config=detector_config)
            policy_metrics = PolicyMetrics(
                matched_rule=decision.matched_rule if decision else None,
                confidence=decision.confidence if decision else 0.5,
                risk_level=get_risk_level(ml_signals),
            )
        
        if preprocessed:
            preprocessing_metrics = PreprocessingMetrics(
                original_length=len(preprocessed.original_text),
                normalized_length=len(preprocessed.normalized_text),
                word_count=preprocessed.features.get("word_count", 0),
                char_count=len(preprocessed.original_text),
            )
        
        latency_breakdown = {
            "preprocessing": metrics.get("preprocessing_latency_ms", 0),
            "ml_analysis": ml_signals.latency_ms if ml_signals else 0,
            "policy_eval": metrics.get("policy_latency_ms", 0),
            "backend": response.get("backend_latency_ms", 0),
        }
        
        return ml_metrics, preprocessing_metrics, policy_metrics, latency_breakdown
    
    @staticmethod
    def extract_from_exception(
        exc: ContentBlockedException,
        detector_config: Optional[Dict] = None
    ) -> Tuple[list, Optional[PreprocessingMetrics], Optional[PolicyMetrics], Dict[str, float]]:
        """
        Extract metrics from a ContentBlockedException.
        
        Returns:
            Tuple of (ml_metrics, preprocessing_metrics, policy_metrics, latency_breakdown)
        """
        ml_metrics = []
        preprocessing_metrics = None
        policy_metrics = None
        latency_breakdown = {}
        
        ml_signals = getattr(exc, "ml_signals", None)
        
        if ml_signals:
            ml_metrics = extract_ml_metrics(ml_signals, detector_config=detector_config)
            policy_metrics = PolicyMetrics(
                matched_rule=exc.details.get("matched_rule"),
                confidence=exc.details.get("confidence", 0.9),
                risk_level=get_risk_level(ml_signals),
            )
            latency_breakdown = {
                "preprocessing": 0,
                "ml_analysis": ml_signals.latency_ms,
                "policy_eval": 0,
                "backend": 0,
            }
        
        if hasattr(exc, "preprocessed") and exc.preprocessed:
            preprocessing_metrics = PreprocessingMetrics(
                original_length=len(exc.preprocessed.original_text),
                normalized_length=len(exc.preprocessed.normalized_text),
                word_count=exc.preprocessed.features.get("word_count", 0),
                char_count=len(exc.preprocessed.original_text),
            )
        
        return ml_metrics, preprocessing_metrics, policy_metrics, latency_breakdown
