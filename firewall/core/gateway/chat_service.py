import time
import uuid
import os
import logging
from typing import Optional

from fastapi import HTTPException, Request, status

from core.exceptions import BackendError, ContentBlockedException, FirewallException
from core.request_context import RequestContext
from core.gateway import create_gateway_orchestrator, get_default_gateway
from core.risk import get_risk_level
from core.events import create_standardized_event
from core.metrics.adapter import extract_ml_metrics
from core.metrics import metrics_service
from core.realtime import event_queue
from core.api_models import (
    ChatRequest,
    ChatResponse,
    PreprocessingMetrics,
    PolicyMetrics,
)


logger = logging.getLogger(__name__)
TENANT_ID = os.getenv("TENANT_ID", "default")


def _generate_request_id() -> str:
    return str(uuid.uuid4())


async def process_chat_request(payload: ChatRequest, request: Request) -> ChatResponse:
    """
    Process the complete chat request using the gateway/firewall.

    Encapsulates all the logic of:
    - Context construction
    - Call to the orchestrator
    - Extraction of metrics
    - Creation of standardized events
    - Registration in metrics and broadcast by WebSocket
    """
    request_id = _generate_request_id()

    # TODO: For now we are using hardcoded values, we need to get them from the request
    # header and calculate the aggregated values
    user_id = (
        request.headers.get("X-User-ID")
        or "96424373-aa08-44ae-98ff-9d63e2981663"
    )
    session_id = (
        request.headers.get("X-Session-ID")
        or "a1e423e8-8486-4309-a660-fdf5b3d55ae9"
    )
    device = request.headers.get("User-Agent", "Unknown")
    temperature = request.headers.get("X-Temperature", 0.5)
    max_tokens = request.headers.get("X-Max-Tokens", 20)
    turn_count = request.headers.get("X-Turn-Count", 1)
    rate_limit = request.headers.get("X-Rate-Limit", 0)

    request_start_time = time.time()
    logger.info("[%s] New chat request: %s...", request_id, payload.message[:50])

    context = RequestContext(
        request_id=request_id,
        user_id=user_id,
        session_id=session_id,
        tenant_id=TENANT_ID,
        endpoint="/api/chat",
        device=device,
        temperature=temperature,
        max_tokens=max_tokens,
        turn_count=turn_count,
        rate_limit_remaining=rate_limit,
    )

    try:
        # Create orchestrator with model configuration if provided,
        # otherwise use the default gateway/firewall.
        current_firewall = (
            create_gateway_orchestrator(model_config=payload.detector_config)
            if payload.detector_config
            else get_default_gateway()
        )

        # Process complete request through the orchestrator
        response = await current_firewall.process_chat_request(
            message=payload.message,
            request_id=request_id,
            analyze_egress=False,
            context=context,
        )

        total_latency = (time.time() - request_start_time) * 1000

        # Extract metrics from response
        ml_metrics = []
        preprocessing_metrics = None
        policy_metrics = None
        latency_breakdown: dict = {}
        ml_signals = None
        preprocessed = None
        decision = None

        if "metrics" in response:
            metrics = response["metrics"]
            ml_signals = metrics.get("ml_signals")
            preprocessed = metrics.get("preprocessed")
            decision = metrics.get("decision")

            # ML Detector metrics with thresholds and status
            if ml_signals:
                ml_metrics = extract_ml_metrics(
                    ml_signals, detector_config=payload.detector_config
                )

                # Policy metrics
                policy_metrics = PolicyMetrics(
                    matched_rule=decision.matched_rule if decision else None,
                    confidence=decision.confidence if decision else 0.5,
                    risk_level=get_risk_level(ml_signals),
                )

            # Preprocessing metrics
            if preprocessed:
                preprocessing_metrics = PreprocessingMetrics(
                    original_length=len(preprocessed.original_text),
                    normalized_length=len(preprocessed.normalized_text),
                    word_count=preprocessed.features.get("word_count", 0),
                    char_count=len(preprocessed.original_text),
                )

            # Latency breakdown
            latency_breakdown = {
                "preprocessing": metrics.get("preprocessing_latency_ms", 0),
                "ml_analysis": ml_signals.latency_ms if ml_signals else 0,
                "policy_eval": metrics.get("policy_latency_ms", 0),
                "backend": response.get("backend_latency_ms", 0),
            }

        # Create standardized event and broadcast
        if ml_signals and preprocessed and decision:
            event = create_standardized_event(
                request_id=request_id,
                prompt=payload.message,
                response=response.get("reply", ""),
                blocked=False,
                ml_signals=ml_signals,
                preprocessed=preprocessed,
                decision=decision,
                latency_breakdown=latency_breakdown,
                total_latency=total_latency,
                session_id=None,  # TODO: Add session tracking
                detector_config=payload.detector_config,
            )

            # Add to metrics service
            metrics_service.add_request(event)

            # Broadcast to WebSocket clients
            if event_queue:
                await event_queue.put(event)

        return ChatResponse(
            blocked=False,
            reply=response.get("reply"),
            ml_detectors=ml_metrics,
            preprocessing=preprocessing_metrics,
            policy=policy_metrics,
            latency_breakdown=latency_breakdown,
            total_latency_ms=total_latency,
        )

    except ContentBlockedException as exc:
        # Blocked by policies
        total_latency = (time.time() - request_start_time) * 1000
        logger.warning("[%s] Blocked by policies: %s", request_id, exc.reason)

        ml_metrics = []
        preprocessing_metrics = None
        policy_metrics = None
        latency_breakdown = {}
        ml_signals = None

        if hasattr(exc, "ml_signals") and exc.ml_signals:
            ml_signals = exc.ml_signals

            # ML Detector metrics
            ml_metrics = extract_ml_metrics(
                ml_signals, detector_config=payload.detector_config
            )

            # Policy metrics
            policy_metrics = PolicyMetrics(
                matched_rule=exc.details.get("matched_rule"),
                confidence=exc.details.get("confidence", 0.9),
                risk_level=get_risk_level(ml_signals),
            )

            # Latency breakdown
            latency_breakdown = {
                "preprocessing": 0,  # Not available in exception
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

        # Create standardized event for blocked request and broadcast
        if ml_signals:
            event = create_standardized_event(
                request_id=request_id,
                prompt=payload.message,
                response=exc.reason,
                blocked=True,
                ml_signals=ml_signals,
                preprocessed=exc.preprocessed if hasattr(exc, "preprocessed") else None,
                decision=type("obj", (object,), {"matched_rule": exc.details.get("matched_rule")})(),
                latency_breakdown=latency_breakdown,
                total_latency=total_latency,
                session_id=None,  # TODO: Add session tracking
                detector_config=payload.detector_config,
            )

            # Add to metrics service
            metrics_service.add_request(event)

            # Broadcast to WebSocket clients
            if event_queue:
                await event_queue.put(event)

        return ChatResponse(
            blocked=True,
            reason=exc.reason,
            ml_detectors=ml_metrics,
            preprocessing=preprocessing_metrics,
            policy=policy_metrics,
            latency_breakdown=latency_breakdown,
            total_latency_ms=total_latency,
        )

    except BackendError as exc:
        logger.error("[%s] Backend error: %s", request_id, exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with the backend: {exc.message}",
        ) from exc

    except FirewallException as exc:
        logger.error("[%s] Firewall error: %s", request_id, exc.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal firewall error: {exc.message}",
        ) from exc

    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[%s] Unexpected error: %s", request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc


