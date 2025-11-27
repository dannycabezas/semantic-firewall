# chat_service.py - Versión Refactorizada

import time
import uuid
import logging
from typing import Optional, Dict, Any

from fastapi import HTTPException, Request, status
from core.gateway.extractors import RequestHeaderExtractor, MetricsExtractor
from core.gateway.builders import RequestContextBuilder
from core.exceptions import BackendError, ContentBlockedException, FirewallException
from core.gateway import create_gateway_orchestrator, get_default_gateway
from core.api_models import (
    ChatRequest,
    ChatResponse,
)
from core.gateway.broadcaster import EventBroadcaster


logger = logging.getLogger(__name__)


class ChatService:
    """Main service for processing chat requests."""
    
    def __init__(
        self,
        header_extractor: RequestHeaderExtractor,
        context_builder: RequestContextBuilder,
        metrics_extractor: MetricsExtractor,
        event_broadcaster: EventBroadcaster,
    ) -> None:
        """Initialize the chat service."""
        self.header_extractor = header_extractor
        self.context_builder = context_builder
        self.metrics_extractor = metrics_extractor
        self.event_broadcaster = event_broadcaster
    
    @staticmethod
    def _generate_request_id() -> str:
        """Generate a unique ID for the request."""
        return str(uuid.uuid4())
    
    async def process_request(
        self,
        payload: ChatRequest,
        request: Request
    ) -> ChatResponse:
        """
        Process a complete chat request.
        
        Orchestrates the complete flow of:
        - Building the context
        - Processing through the firewall
        - Extracting metrics
        - Broadcasting events
        """
        request_id = self._generate_request_id()
        request_start_time = time.time()
        
        logger.info("[%s] New chat request: %s...", request_id, payload.message[:50])
        
        # Extract headers and build context
        headers = self.header_extractor.extract(request)
        context = self.context_builder.build(request_id, headers)
        
        try:
            # Get firewall/orchestrator
            firewall = self._get_firewall(payload.detector_config)
            
            # Process through firewall
            response = await firewall.process_chat_request(
                message=payload.message,
                request_id=request_id,
                analyze_egress=False,
                context=context,
            )
            
            total_latency = (time.time() - request_start_time) * 1000
            
            # Handle successful response
            return await self._handle_success_response(
                response=response,
                payload=payload,
                request_id=request_id,
                total_latency=total_latency,
            )
        
        except ContentBlockedException as exc:
            return await self._handle_blocked_request(
                exc=exc,
                payload=payload,
                request_id=request_id,
                request_start_time=request_start_time,
            )
        
        except BackendError as exc:
            self._handle_backend_error(request_id, exc)
        
        except FirewallException as exc:
            self._handle_firewall_error(request_id, exc)
        
        except Exception as exc:
            self._handle_unexpected_error(request_id, exc)
    
    def _get_firewall(self, detector_config: Optional[Dict]):
        """Get the appropriate firewall based on the configuration."""
        if detector_config:
            return create_gateway_orchestrator(model_config=detector_config)
        return get_default_gateway()
    
    async def _handle_success_response(
        self,
        response: Dict[str, Any],
        payload: ChatRequest,
        request_id: str,
        total_latency: float,
    ) -> ChatResponse:
        """Handles a successful firewall response."""
        # Extract metrics
        ml_metrics, preprocessing_metrics, policy_metrics, latency_breakdown = (
            self.metrics_extractor.extract_from_response(
                response, payload.detector_config
            )
        )
        
        # Create and broadcast event
        metrics = response.get("metrics", {})
        ml_signals = metrics.get("ml_signals")
        preprocessed = metrics.get("preprocessed")
        decision = metrics.get("decision")
        
        if ml_signals and preprocessed and decision:
            await self.event_broadcaster.create_and_broadcast_event(
                request_id=request_id,
                prompt=payload.message,
                response_text=response.get("reply", ""),
                blocked=False,
                ml_signals=ml_signals,
                preprocessed=preprocessed,
                decision=decision,
                latency_breakdown=latency_breakdown,
                total_latency=total_latency,
                detector_config=payload.detector_config,
            )
        
        return ChatResponse(
            blocked=False,
            reply=response.get("reply"),
            ml_detectors=ml_metrics,
            preprocessing=preprocessing_metrics,
            policy=policy_metrics,
            latency_breakdown=latency_breakdown,
            total_latency_ms=total_latency,
        )
    
    async def _handle_blocked_request(
        self,
        exc: ContentBlockedException,
        payload: ChatRequest,
        request_id: str,
        request_start_time: float,
    ) -> ChatResponse:
        """Handles a request blocked by policies."""
        total_latency = (time.time() - request_start_time) * 1000
        logger.warning("[%s] Blocked by policies: %s", request_id, exc.reason)
        
        # Extract metrics
        ml_metrics, preprocessing_metrics, policy_metrics, latency_breakdown = (
            self.metrics_extractor.extract_from_exception(exc, payload.detector_config)
        )
        
        # Create and broadcast event
        ml_signals = getattr(exc, "ml_signals", None)
        if ml_signals:
            # Create a simple decision object for blocked requests
            decision = type("Decision", (), {
                "matched_rule": exc.details.get("matched_rule")
            })()
            
            await self.event_broadcaster.create_and_broadcast_event(
                request_id=request_id,
                prompt=payload.message,
                response_text=exc.reason,
                blocked=True,
                ml_signals=ml_signals,
                preprocessed=getattr(exc, "preprocessed", None),
                decision=decision,
                latency_breakdown=latency_breakdown,
                total_latency=total_latency,
                detector_config=payload.detector_config,
            )
        
        return ChatResponse(
            blocked=True,
            reason=exc.reason,
            ml_detectors=ml_metrics,
            preprocessing=preprocessing_metrics,
            policy=policy_metrics,
            latency_breakdown=latency_breakdown,
            total_latency_ms=total_latency,
        )
    
    def _handle_backend_error(self, request_id: str, exc: BackendError):
        """Handles backend errors."""
        logger.error("[%s] Backend error: %s", request_id, exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with the backend: {exc.message}",
        ) from exc
    
    def _handle_firewall_error(self, request_id: str, exc: FirewallException):
        """Handles firewall errors."""
        logger.error("[%s] Firewall error: %s", request_id, exc.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal firewall error: {exc.message}",
        ) from exc
    
    def _handle_unexpected_error(self, request_id: str, exc: Exception):
        """Handles unexpected errors."""
        logger.exception("[%s] Unexpected error: %s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc


def create_chat_service() -> ChatService:
    """Create a chat service instance with all its dependencies."""
    return ChatService(
        header_extractor=RequestHeaderExtractor(),
        context_builder=RequestContextBuilder(),
        metrics_extractor=MetricsExtractor(),
        event_broadcaster=EventBroadcaster(),
    )


_chat_service = create_chat_service()


async def process_chat_request(payload: ChatRequest, request: Request) -> ChatResponse:
    """
    Process a complete chat request.
    
    This function maintains the public interface for compatibility.
    """
    return await _chat_service.process_request(payload, request)