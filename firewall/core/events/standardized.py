from datetime import datetime
from typing import Optional, Any

from fast_ml_filter.ml_filter_service import MLSignals

from core.risk import get_risk_level, determine_risk_category


def create_standardized_event(
    request_id: str,
    prompt: str,
    response: str,
    blocked: bool,
    ml_signals: MLSignals,
    preprocessed: Any,
    decision: Any,
    latency_breakdown: dict[str, float],
    total_latency: float,
    session_id: Optional[str] = None,
    detector_config: Optional[dict] = None,
) -> dict[str, Any]:
    """Create a standardized event dictionary for the dashboard / WebSocket.

    Args:
        request_id: Unique request ID
        prompt: User prompt
        response: Response from the firewall
        blocked: Whether the request was blocked
        ml_signals: ML signals from the firewall
        preprocessed: Preprocessed text
        decision: Decision from the firewall
        latency_breakdown: Latency breakdown
        total_latency: Total latency
        session_id: Session ID
        detector_config: Detector configuration

    Returns:
        Standardized event dictionary
    """
    risk_level = get_risk_level(ml_signals)
    risk_category = determine_risk_category(ml_signals)

    risk_level_map = {
        "low": "benign",
        "medium": "suspicious",
        "high": "suspicious",
        "critical": "malicious",
    }
    standard_risk_level = risk_level_map.get(risk_level, "benign")

    scores = {
        "prompt_injection": getattr(ml_signals, "prompt_injection_score", 0.0),
        "pii": getattr(ml_signals, "pii_score", 0.0),
        "toxicity": getattr(ml_signals, "toxicity_score", 0.0),
        "heuristic": 1.0 if ml_signals.heuristic_blocked else 0.0,
    }

    heuristics = []
    if ml_signals.heuristic_blocked:
        heuristics.append("heuristic_match")

    event = {
        "id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt": prompt[:500] if len(prompt) > 500 else prompt,
        "response": response[:500] if len(response) > 500 else response,
        "risk_level": standard_risk_level,
        "risk_category": risk_category,
        "scores": scores,
        "heuristics": heuristics,
        "policy": {
            "matched_rule": decision.matched_rule if decision else None,
            "decision": "block" if blocked else "allow",
        },
        "action": "block" if blocked else "allow",
        "latency_ms": {
            "preprocessing": latency_breakdown.get("preprocessing", 0),
            "ml": latency_breakdown.get("ml_analysis", 0),
            "policy": latency_breakdown.get("policy_eval", 0),
            "backend": latency_breakdown.get("backend", 0),
            "total": total_latency,
        },
        "session_id": session_id,
        "preprocessing_info": {
            "original_length": len(preprocessed.original_text) if preprocessed else 0,
            "normalized_length": len(preprocessed.normalized_text) if preprocessed else 0,
            "word_count": preprocessed.features.get("word_count", 0) if preprocessed else 0,
        }
        if preprocessed
        else None,
        "detector_config": detector_config,
    }

    return event


