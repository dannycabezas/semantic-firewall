from fast_ml_filter.ml_filter_service import MLSignals


def get_risk_level(ml_signals: MLSignals) -> str:
    """Calculate the global risk level from the ML signals."""
    max_score = max(
        ml_signals.pii_score,
        ml_signals.toxicity_score,
        ml_signals.prompt_injection_score,
    )
    if max_score >= 0.8 or ml_signals.heuristic_blocked:
        return "critical"
    elif max_score >= 0.6:
        return "high"
    elif max_score >= 0.3:
        return "medium"
    return "low"


def determine_risk_category(ml_signals: MLSignals) -> str:
    """Determine the main risk category from the ML signals."""
    scores = {
        "injection": (
            ml_signals.prompt_injection_score
            if hasattr(ml_signals, "prompt_injection_score")
            else 0
        ),
        "pii": ml_signals.pii_score if hasattr(ml_signals, "pii_score") else 0,
        "toxicity": (
            ml_signals.toxicity_score
            if hasattr(ml_signals, "toxicity_score")
            else 0
        ),
    }

    # First check if the heuristic blocks
    if ml_signals.heuristic_blocked:
        return "leak"  # Indicates attempts to leak information

    max_category = max(scores, key=scores.get)
    if scores[max_category] > 0.3:
        return max_category

    return "clean"


