from typing import Any, Dict, Optional
from core.events import create_standardized_event
from core.metrics import metrics_service
from core.realtime import event_queue


class EventBroadcaster:
    """Manages the creation and broadcasting of standardized events."""
    
    @staticmethod
    async def create_and_broadcast_event(
        request_id: str,
        prompt: str,
        response_text: str,
        blocked: bool,
        ml_signals: Any,
        preprocessed: Any,
        decision: Any,
        latency_breakdown: Dict[str, float],
        total_latency: float,
        detector_config: Optional[Dict] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Create a standardized event and broadcast it."""
        if not ml_signals:
            return
        
        event = create_standardized_event(
            request_id=request_id,
            prompt=prompt,
            response=response_text,
            blocked=blocked,
            ml_signals=ml_signals,
            preprocessed=preprocessed,
            decision=decision,
            latency_breakdown=latency_breakdown,
            total_latency=total_latency,
            session_id=session_id,
            detector_config=detector_config,
        )
        
        # Add to metrics service
        metrics_service.add_request(event)
        
        # Broadcast to WebSocket clients
        if event_queue:
            await event_queue.put(event)
