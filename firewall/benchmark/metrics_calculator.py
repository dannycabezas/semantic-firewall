"""Metrics calculation for benchmark results."""

from typing import List, Dict, Any
import numpy as np


class MetricsCalculator:
    """Calculate classification metrics from benchmark results."""
    
    @staticmethod
    def calculate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics from benchmark results.
        
        Args:
            results: List of result dictionaries with 'result_type' and 'latency_ms'
            
        Returns:
            Dictionary with calculated metrics
        """
        # Count result types
        tp = sum(1 for r in results if r["result_type"] == "TRUE_POSITIVE")
        fp = sum(1 for r in results if r["result_type"] == "FALSE_POSITIVE")
        tn = sum(1 for r in results if r["result_type"] == "TRUE_NEGATIVE")
        fn = sum(1 for r in results if r["result_type"] == "FALSE_NEGATIVE")
        
        total = tp + fp + tn + fn
        
        # Calculate classification metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / total if total > 0 else 0.0
        
        # Calculate latency metrics
        latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
        
        latency_metrics = {}
        if latencies:
            latency_metrics = {
                "avg_latency_ms": float(np.mean(latencies)),
                "p50_latency_ms": float(np.percentile(latencies, 50)),
                "p95_latency_ms": float(np.percentile(latencies, 95)),
                "p99_latency_ms": float(np.percentile(latencies, 99))
            }
        
        return {
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "accuracy": round(accuracy, 4),
            "total_samples": total,
            **latency_metrics
        }
    
    @staticmethod
    def calculate_result_type(
        expected_label: str,
        predicted_blocked: bool
    ) -> str:
        """
        Determine the result type based on expected label and prediction.
        
        Args:
            expected_label: "jailbreak" or "benign"
            predicted_blocked: Whether the firewall blocked the request
            
        Returns:
            Result type: TRUE_POSITIVE, FALSE_POSITIVE, TRUE_NEGATIVE, or FALSE_NEGATIVE
        """
        expected_malicious = (expected_label == "jailbreak")
        predicted_malicious = predicted_blocked
        
        if expected_malicious and predicted_malicious:
            return "TRUE_POSITIVE"
        elif expected_malicious and not predicted_malicious:
            return "FALSE_NEGATIVE"
        elif not expected_malicious and predicted_malicious:
            return "FALSE_POSITIVE"
        else:  # not expected_malicious and not predicted_malicious
            return "TRUE_NEGATIVE"

