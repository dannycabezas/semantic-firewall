from typing import Optional, List

from fast_ml_filter.ml_filter_service import MLSignals

from core.api_models import DetectorMetrics  # Shared model with the API layer


def _get_status(score: float, threshold: float) -> str:
    """Get status based on score and threshold."""
    if score >= threshold:
        return "block"
    elif score >= threshold * 0.7:
        return "warn"
    return "pass"


def extract_ml_metrics(
    ml_signals: MLSignals, detector_config: Optional[dict] = None
) -> List[DetectorMetrics]:
    """
    Extract ML detector metrics with thresholds and status.

    Args:
        ml_signals: ML signals from the firewall
        detector_config: Detector configuration

    Returns:
        List of DetectorMetrics
    """
    thresholds = {
        "pii": 0.8,
        "toxicity": 0.7,
        "prompt_injection": 0.8,
        "heuristic": 1.0,
    }

    model_names = {
        "pii": detector_config.get("pii", "presidio") if detector_config else "presidio",
        "toxicity": detector_config.get("toxicity", "detoxify")
        if detector_config
        else "detoxify",
        "prompt_injection": detector_config.get("prompt_injection", "custom_onnx")
        if detector_config
        else "custom_onnx",
    }

    model_display_names = {
        "presidio": "Presidio",
        "onnx": "ONNX",
        "mock": "Mock",
        "detoxify": "Detoxify",
        "custom_onnx": "Custom ONNX",
        "deberta": "DeBERTa",
    }

    metrics: List[DetectorMetrics] = []

    if hasattr(ml_signals, "pii_metrics") and ml_signals.pii_metrics:
        model_name = model_names.get("pii", "presidio")
        metrics.append(
            DetectorMetrics(
                name="PII Detector",
                score=ml_signals.pii_metrics.score,
                latency_ms=ml_signals.pii_metrics.latency_ms,
                threshold=thresholds["pii"],
                status=_get_status(ml_signals.pii_metrics.score, thresholds["pii"]),
                model_name=model_display_names.get(model_name, model_name),
            )
        )

    if hasattr(ml_signals, "toxicity_metrics") and ml_signals.toxicity_metrics:
        model_name = model_names.get("toxicity", "detoxify")
        metrics.append(
            DetectorMetrics(
                name="Toxicity Detector",
                score=ml_signals.toxicity_metrics.score,
                latency_ms=ml_signals.toxicity_metrics.latency_ms,
                threshold=thresholds["toxicity"],
                status=_get_status(
                    ml_signals.toxicity_metrics.score, thresholds["toxicity"]
                ),
                model_name=model_display_names.get(model_name, model_name),
            )
        )

    if hasattr(ml_signals, "prompt_injection_metrics") and ml_signals.prompt_injection_metrics:
        model_name = model_names.get("prompt_injection", "custom_onnx")
        metrics.append(
            DetectorMetrics(
                name="Prompt Injection Detector",
                score=ml_signals.prompt_injection_metrics.score,
                latency_ms=ml_signals.prompt_injection_metrics.latency_ms,
                threshold=thresholds["prompt_injection"],
                status=_get_status(
                    ml_signals.prompt_injection_metrics.score,
                    thresholds["prompt_injection"],
                ),
                model_name=model_display_names.get(model_name, model_name),
            )
        )

    if hasattr(ml_signals, "heuristic_metrics") and ml_signals.heuristic_metrics:
        heuristic_score = ml_signals.heuristic_metrics.score
        metrics.append(
            DetectorMetrics(
                name="Heuristic Detector",
                score=heuristic_score,
                latency_ms=ml_signals.heuristic_metrics.latency_ms,
                threshold=thresholds["heuristic"],
                status="block" if heuristic_score >= 1.0 else "pass",
                model_name="Regex",
            )
        )

    return metrics


