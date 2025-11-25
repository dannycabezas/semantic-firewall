"""
Metrics Manager for SPG Semantic Firewall Dashboard.

Manages in-memory storage of requests, KPI calculations, and analytics.
"""
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RequestEvent:
    """Represents a single request event with all metrics."""

    id: str
    timestamp: str
    prompt: str
    response: str
    risk_level: str  # benign | suspicious | malicious
    risk_category: str  # injection | pii | toxicity | leak | harmful | clean
    scores: Dict[str, float]
    heuristics: List[str]
    policy: Dict[str, str]
    action: str  # allow | block
    latency_ms: Dict[str, float]
    session_id: Optional[str] = None
    preprocessing_info: Optional[Dict[str, int]] = None
    detector_config: Optional[Dict[str, str]] = None


@dataclass
class SessionInfo:
    """Tracks session-level analytics."""

    session_id: str
    total_requests: int = 0
    malicious_count: int = 0
    suspicious_count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


class MetricsManager:
    """
    Thread-safe manager for firewall metrics and analytics.

    Stores last N requests in memory and provides KPI calculations.
    """

    def __init__(self, max_requests: int = 500):
        """
        Initialize the metrics manager.

        Args:
            max_requests: Maximum number of requests to store in memory
        """
        self._max_requests = max_requests
        self._requests: deque[RequestEvent] = deque(maxlen=max_requests)
        self._sessions: Dict[str, SessionInfo] = {}
        self._lock = threading.RLock()
        logger.info(f"MetricsManager initialized with max_requests={max_requests}")

    def add_request(self, event: RequestEvent) -> None:
        """
        Add a new request event to the metrics store.

        Args:
            event: RequestEvent to add
        """
        with self._lock:
            self._requests.append(event)

            # Update session analytics if session_id is present
            if event.session_id:
                if event.session_id not in self._sessions:
                    self._sessions[event.session_id] = SessionInfo(
                        session_id=event.session_id
                    )

                session = self._sessions[event.session_id]
                session.total_requests += 1
                session.last_seen = datetime.now()

                if event.risk_level == "malicious":
                    session.malicious_count += 1
                elif event.risk_level == "suspicious":
                    session.suspicious_count += 1

            logger.debug(
                f"Added request {event.id}, total requests: {len(self._requests)}"
            )

    def get_stats(self) -> Dict:
        """
        Calculate and return executive KPIs and statistics.

        Returns:
            Dictionary with KPIs and aggregated stats
        """
        with self._lock:
            if not self._requests:
                return self._empty_stats()

            total = len(self._requests)
            benign = sum(1 for r in self._requests if r.risk_level == "benign")
            suspicious = sum(1 for r in self._requests if r.risk_level == "suspicious")
            malicious = sum(1 for r in self._requests if r.risk_level == "malicious")
            blocked = sum(1 for r in self._requests if r.action == "block")
            allowed = total - blocked

            # Calculate percentages
            benign_pct = (benign / total * 100) if total > 0 else 0
            suspicious_pct = (suspicious / total * 100) if total > 0 else 0
            malicious_pct = (malicious / total * 100) if total > 0 else 0

            # Calculate ratio
            ratio = f"1:{allowed // blocked if blocked > 0 else allowed}"

            # Calculate prompts per minute (last 5 minutes)
            now = datetime.now(timezone.utc)
            five_min_ago = now - timedelta(minutes=5)
            recent = [
                r for r in self._requests if datetime.fromisoformat(r.timestamp.replace("Z", "+00:00")) > five_min_ago
            ]
            prompts_per_min = len(recent) / 5 if recent else 0

            # Calculate average latencies
            avg_latency = {
                "preprocessing": sum(
                    r.latency_ms.get("preprocessing", 0) for r in self._requests
                )
                / total,
                "ml": sum(r.latency_ms.get("ml", 0) for r in self._requests) / total,
                "policy": sum(r.latency_ms.get("policy", 0) for r in self._requests)
                / total,
                "backend": sum(r.latency_ms.get("backend", 0) for r in self._requests)
                / total,
                "total": sum(r.latency_ms.get("total", 0) for r in self._requests)
                / total,
            }

            # Risk trend (compare last 10% vs previous)
            split_point = max(1, total // 10)
            recent_slice = list(self._requests)[-split_point:]
            previous_slice = list(self._requests)[:-split_point] if total > split_point else []
            
            recent_risk_avg = (
                sum(self._risk_level_to_score(r.risk_level) for r in recent_slice)
                / len(recent_slice)
                if recent_slice
                else 0
            )
            previous_risk_avg = (
                sum(self._risk_level_to_score(r.risk_level) for r in previous_slice)
                / len(previous_slice)
                if previous_slice
                else 0
            )
            
            risk_trend = "increasing" if recent_risk_avg > previous_risk_avg else "decreasing" if recent_risk_avg < previous_risk_avg else "stable"

            return {
                "total_prompts": total,
                "benign_count": benign,
                "suspicious_count": suspicious,
                "malicious_count": malicious,
                "benign_pct": round(benign_pct, 1),
                "suspicious_pct": round(suspicious_pct, 1),
                "malicious_pct": round(malicious_pct, 1),
                "blocked_count": blocked,
                "allowed_count": allowed,
                "block_allow_ratio": ratio,
                "prompts_per_minute": round(prompts_per_min, 2),
                "risk_trend": risk_trend,
                "avg_latency_ms": avg_latency,
                "risk_breakdown": self.get_risk_breakdown(),
            }

    def get_recent(self, limit: int = 50) -> List[Dict]:
        """
        Get the most recent N requests.

        Args:
            limit: Maximum number of requests to return

        Returns:
            List of request events as dictionaries
        """
        with self._lock:
            recent = list(self._requests)[-limit:]
            return [self._event_to_dict(event) for event in reversed(recent)]

    def get_risk_breakdown(self) -> Dict[str, int]:
        """
        Get breakdown of requests by risk category.

        Returns:
            Dictionary mapping risk categories to counts
        """
        with self._lock:
            breakdown = {
                "injection": 0,
                "pii": 0,
                "toxicity": 0,
                "leak": 0,
                "harmful": 0,
                "clean": 0,
            }

            for req in self._requests:
                category = req.risk_category
                if category in breakdown:
                    breakdown[category] += 1

            return breakdown

    def get_session_analytics(self, top_n: int = 5) -> List[Dict]:
        """
        Get analytics for top N sessions with most suspicious/malicious activity.

        Args:
            top_n: Number of top sessions to return

        Returns:
            List of session analytics dictionaries
        """
        with self._lock:
            # Sort sessions by malicious + suspicious count
            sorted_sessions = sorted(
                self._sessions.values(),
                key=lambda s: s.malicious_count + s.suspicious_count,
                reverse=True,
            )

            return [
                {
                    "session_id": s.session_id,
                    "total_requests": s.total_requests,
                    "malicious_count": s.malicious_count,
                    "suspicious_count": s.suspicious_count,
                    "first_seen": s.first_seen.isoformat(),
                    "last_seen": s.last_seen.isoformat(),
                }
                for s in sorted_sessions[:top_n]
            ]

    def get_temporal_breakdown(self, minutes: int = 10) -> Dict[str, List]:
        """
        Get temporal breakdown of risk categories over last N minutes.

        Args:
            minutes: Number of minutes to analyze

        Returns:
            Dictionary with timestamps and category counts
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(minutes=minutes)

            # Group requests by minute
            minute_buckets = {}
            for req in self._requests:
                req_time = datetime.fromisoformat(req.timestamp.replace("Z", "+00:00"))
                if req_time > cutoff:
                    minute_key = req_time.strftime("%Y-%m-%d %H:%M")
                    if minute_key not in minute_buckets:
                        minute_buckets[minute_key] = {
                            "injection": 0,
                            "pii": 0,
                            "toxicity": 0,
                            "leak": 0,
                            "harmful": 0,
                            "clean": 0,
                        }
                    minute_buckets[minute_key][req.risk_category] += 1

            # Convert to arrays sorted by time
            timestamps = sorted(minute_buckets.keys())
            return {
                "timestamps": timestamps,
                "categories": {
                    category: [minute_buckets[ts][category] for ts in timestamps]
                    for category in ["injection", "pii", "toxicity", "leak", "harmful", "clean"]
                },
            }

    @staticmethod
    def _risk_level_to_score(risk_level: str) -> float:
        """Convert risk level to numeric score for trend calculation."""
        return {"benign": 0, "suspicious": 0.5, "malicious": 1.0}.get(risk_level, 0)

    @staticmethod
    def _empty_stats() -> Dict:
        """Return empty stats structure."""
        return {
            "total_prompts": 0,
            "benign_count": 0,
            "suspicious_count": 0,
            "malicious_count": 0,
            "benign_pct": 0,
            "suspicious_pct": 0,
            "malicious_pct": 0,
            "blocked_count": 0,
            "allowed_count": 0,
            "block_allow_ratio": "1:0",
            "prompts_per_minute": 0,
            "risk_trend": "stable",
            "avg_latency_ms": {
                "preprocessing": 0,
                "ml": 0,
                "policy": 0,
                "backend": 0,
                "total": 0,
            },
            "risk_breakdown": {
                "injection": 0,
                "pii": 0,
                "toxicity": 0,
                "leak": 0,
                "harmful": 0,
                "clean": 0,
            },
        }

    @staticmethod
    def _event_to_dict(event: RequestEvent) -> Dict:
        """Convert RequestEvent to dictionary."""
        return {
            "id": event.id,
            "timestamp": event.timestamp,
            "prompt": event.prompt,
            "response": event.response,
            "risk_level": event.risk_level,
            "risk_category": event.risk_category,
            "scores": event.scores,
            "heuristics": event.heuristics,
            "policy": event.policy,
            "action": event.action,
            "latency_ms": event.latency_ms,
            "session_id": event.session_id,
            "preprocessing_info": event.preprocessing_info,
            "detector_config": event.detector_config,
        }

