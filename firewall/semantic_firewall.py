import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from container import FirewallContainer
from core.analyzer import FirewallAnalyzer
from core.backend_proxy import BackendProxyService
from core.exceptions import (BackendError, ContentBlockedException,
                             FirewallException)
from core.orchestrator import FirewallOrchestrator
from fast_ml_filter.ml_filter_service import MLSignals
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status, Request
from fastapi.middleware.cors import CORSMiddleware
from metrics_manager import MetricsManager, RequestEvent
from pydantic import BaseModel
from core.request_context import RequestContext
from benchmark.database import BenchmarkDatabase
from benchmark.benchmark_runner import BenchmarkRunner
from benchmark.dataset_loader import DatasetLoader


DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"
if DEBUG_MODE:
    import debugpy

    debugpy.listen(("0.0.0.0", 5678))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
TENANT_ID = os.getenv("TENANT_ID", "default")

container = FirewallContainer()

# Initialize MetricsManager
metrics_manager = MetricsManager(max_requests=500)

# Event queue for WebSocket broadcasts
event_queue: asyncio.Queue = None

# Initialize Benchmark components
BENCHMARK_DB_PATH = os.getenv("BENCHMARK_DB_PATH", "benchmarks.db")
benchmark_database: Optional[BenchmarkDatabase] = None
benchmark_runner: Optional[BenchmarkRunner] = None


class ConnectionManager:
    """Manages WebSocket connections with heartbeat."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 90  # seconds

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to websocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected WebSockets."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def heartbeat_sender(self, websocket: WebSocket):
        """Send periodic heartbeat pings to keep connection alive."""
        try:
            while websocket in self.active_connections:
                await asyncio.sleep(self.heartbeat_interval)
                if websocket in self.active_connections:
                    await websocket.send_json({"type": "ping"})
        except Exception as e:
            logger.error(f"Heartbeat sender error: {e}")
            self.disconnect(websocket)


manager = ConnectionManager()


def create_firewall_orchestrator(model_config: Optional[dict] = None) -> FirewallOrchestrator:
    """
    Factory to create the firewall orchestrator.
    
    Args:
        model_config: Optional dictionary with model configuration:
            {
                "prompt_injection": "custom_onnx" | "deberta",
                "pii": "presidio" | "onnx" | "mock",
                "toxicity": "detoxify" | "onnx"
            }
            If None, uses default models from container.
    """
    # Create ML filter service with specified models or use default
    if model_config:
        from fast_ml_filter.ml_filter_service import MLFilterService
        ml_filter = MLFilterService.create_with_models(model_config=model_config)
    else:
        ml_filter = container.ml_filter_service()
    
    analyzer = FirewallAnalyzer(
        preprocessor=container.preprocessor_service(),
        ml_filter=ml_filter,
        policy_engine=container.policy_service(),
        tenant_id=TENANT_ID,
    )

    proxy = BackendProxyService(backend_url=BACKEND_URL, timeout=30.0)

    orchestrator = container.orchestrator_service()

    return FirewallOrchestrator(
        analyzer=analyzer,
        proxy=proxy,
        orchestrator=orchestrator,
    )


firewall = create_firewall_orchestrator()

app = FastAPI(title="SPG Semantic Firewall")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize event queue and background tasks on startup."""
    global event_queue
    event_queue = asyncio.Queue()
    asyncio.create_task(event_broadcaster())
    logger.info("SPG Semantic Firewall started with WebSocket support")


async def event_broadcaster():
    """Background task to broadcast events from queue to all WebSocket clients."""
    global event_queue
    while True:
        try:
            event = await event_queue.get()
            await manager.broadcast(event)
        except Exception as e:
            logger.error(f"Error in event broadcaster: {e}")


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


def generate_request_id() -> str:
    return str(uuid.uuid4())


def get_risk_level(ml_signals: MLSignals) -> str:
    """Calculate overall risk level."""
    max_score = max(
        ml_signals.pii_score,
        ml_signals.toxicity_score,
        ml_signals.prompt_injection_score
    )
    if max_score >= 0.8 or ml_signals.heuristic_blocked:
        return "critical"
    elif max_score >= 0.6:
        return "high"
    elif max_score >= 0.3:
        return "medium"
    return "low"


def get_status(score: float, threshold: float) -> str:
    """Get status based on score and threshold."""
    if score >= threshold:
        return "block"
    elif score >= threshold * 0.7:
        return "warn"
    return "pass"


def determine_risk_category(ml_signals: MLSignals) -> str:
    """Determine primary risk category from ML signals."""
    scores = {
        "injection": ml_signals.prompt_injection_score if hasattr(ml_signals, 'prompt_injection_score') else 0,
        "pii": ml_signals.pii_score if hasattr(ml_signals, 'pii_score') else 0,
        "toxicity": ml_signals.toxicity_score if hasattr(ml_signals, 'toxicity_score') else 0,
    }
    
    # Check heuristic block first
    if ml_signals.heuristic_blocked:
        return "leak"  # Heuristic blocks often indicate leak attempts
    
    # Find highest score
    max_category = max(scores, key=scores.get)
    if scores[max_category] > 0.3:
        return max_category
    
    return "clean"


def create_standardized_event(
    request_id: str,
    prompt: str,
    response: str,
    blocked: bool,
    ml_signals: MLSignals,
    preprocessed,
    decision,
    latency_breakdown: dict,
    total_latency: float,
    session_id: str = None,
    detector_config: Optional[dict] = None
) -> dict:
    """
    Create a standardized event dictionary for WebSocket broadcast.
    
    Args:
        request_id: Unique request ID
        prompt: User prompt
        response: Response or block reason
        blocked: Whether request was blocked
        ml_signals: ML analysis signals
        preprocessed: Preprocessed data
        decision: Policy decision
        latency_breakdown: Breakdown of latencies
        total_latency: Total latency
        session_id: Optional session ID
        detector_config: Optional detector configuration with model names
        
    Returns:
        Standardized event dictionary
    """
    risk_level = get_risk_level(ml_signals)
    risk_category = determine_risk_category(ml_signals)
    
    # Map risk level to our standard levels
    risk_level_map = {
        "low": "benign",
        "medium": "suspicious",
        "high": "suspicious",
        "critical": "malicious"
    }
    standard_risk_level = risk_level_map.get(risk_level, "benign")
    
    # Extract scores
    scores = {
        "prompt_injection": getattr(ml_signals, 'prompt_injection_score', 0.0),
        "pii": getattr(ml_signals, 'pii_score', 0.0),
        "toxicity": getattr(ml_signals, 'toxicity_score', 0.0),
        "heuristic": 1.0 if ml_signals.heuristic_blocked else 0.0,
    }
    
    # Extract heuristics
    heuristics = []
    if ml_signals.heuristic_blocked:
        heuristics.append("heuristic_match")
    
    # Build event
    event = {
        "id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prompt": prompt[:500] if len(prompt) > 500 else prompt,  # Truncate long prompts
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
        } if preprocessed else None,
        "detector_config": detector_config,
    }
    
    return event


def extract_ml_metrics(ml_signals: MLSignals, detector_config: Optional[dict] = None) -> list[DetectorMetrics]:
    """Extract ML detector metrics with thresholds and status."""
    # Thresholds from policies.rego
    thresholds = {
        "pii": 0.8,
        "toxicity": 0.7,
        "prompt_injection": 0.8,
        "heuristic": 1.0
    }
    
    # Get model names from detector_config or use defaults
    model_names = {
        "pii": detector_config.get("pii", "presidio") if detector_config else "presidio",
        "toxicity": detector_config.get("toxicity", "detoxify") if detector_config else "detoxify",
        "prompt_injection": detector_config.get("prompt_injection", "custom_onnx") if detector_config else "custom_onnx",
    }
    
    # Map model names to display names
    model_display_names = {
        "presidio": "Presidio",
        "onnx": "ONNX",
        "mock": "Mock",
        "detoxify": "Detoxify",
        "custom_onnx": "Custom ONNX",
        "deberta": "DeBERTa",
    }
    
    metrics = []
    
    if hasattr(ml_signals, 'pii_metrics') and ml_signals.pii_metrics:
        model_name = model_names.get("pii", "presidio")
        metrics.append(DetectorMetrics(
            name="PII Detector",
            score=ml_signals.pii_metrics.score,
            latency_ms=ml_signals.pii_metrics.latency_ms,
            threshold=thresholds["pii"],
            status=get_status(ml_signals.pii_metrics.score, thresholds["pii"]),
            model_name=model_display_names.get(model_name, model_name)
        ))
    
    if hasattr(ml_signals, 'toxicity_metrics') and ml_signals.toxicity_metrics:
        model_name = model_names.get("toxicity", "detoxify")
        metrics.append(DetectorMetrics(
            name="Toxicity Detector",
            score=ml_signals.toxicity_metrics.score,
            latency_ms=ml_signals.toxicity_metrics.latency_ms,
            threshold=thresholds["toxicity"],
            status=get_status(ml_signals.toxicity_metrics.score, thresholds["toxicity"]),
            model_name=model_display_names.get(model_name, model_name)
        ))
    
    if hasattr(ml_signals, 'prompt_injection_metrics') and ml_signals.prompt_injection_metrics:
        model_name = model_names.get("prompt_injection", "custom_onnx")
        metrics.append(DetectorMetrics(
            name="Prompt Injection Detector",
            score=ml_signals.prompt_injection_metrics.score,
            latency_ms=ml_signals.prompt_injection_metrics.latency_ms,
            threshold=thresholds["prompt_injection"],
            status=get_status(ml_signals.prompt_injection_metrics.score, thresholds["prompt_injection"]),
            model_name=model_display_names.get(model_name, model_name)
        ))
    
    if hasattr(ml_signals, 'heuristic_metrics') and ml_signals.heuristic_metrics:
        heuristic_score = ml_signals.heuristic_metrics.score
        metrics.append(DetectorMetrics(
            name="Heuristic Detector",
            score=heuristic_score,
            latency_ms=ml_signals.heuristic_metrics.latency_ms,
            threshold=thresholds["heuristic"],
            status="block" if heuristic_score >= 1.0 else "pass",
            model_name="Regex"
        ))
    
    return metrics


# === ENDPOINTS ===
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, request: Request) -> ChatResponse:
    """
    Endpoint principal of chat with firewall integrated.

    Flow:
    1. Analysis ingress (preprocess + ML + policies)
    2. Proxy to backend (if passes the firewall)
    3. Analysis egress (backend response)
    4. Return response or block

    Args:
        payload: User message

    Returns:
        Backend response or block message con métricas de detectores

    Raises:
        HTTPException: En caso de error
    """
    import time

    # TODO: For now we are using hardcoded values, we need to get them from the request 
    # header and calculate the aggregated values
    
    request_id = generate_request_id()
    user_id = request.headers.get("X-User-ID") or "96424373-aa08-44ae-98ff-9d63e2981663"
    session_id = request.headers.get("X-Session-ID") or "a1e423e8-8486-4309-a660-fdf5b3d55ae9"
    device = request.headers.get("User-Agent", "Unknown")
    temperature = request.headers.get("X-Temperature", 0.5)
    max_tokens = request.headers.get("X-Max-Tokens", 20)
    turn_count = request.headers.get("X-Turn-Count", 1)
    rate_limit = request.headers.get("X-Rate-Limit", 0)

    request_start_time = time.time()
    logger.info(f"[{request_id}] New chat request: {payload.message[:50]}...")

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
        # Create orchestrator with model config if provided, otherwise use default
        current_firewall = create_firewall_orchestrator(model_config=payload.detector_config) if payload.detector_config else firewall
        
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
        latency_breakdown = {}
        
        if "metrics" in response:
            metrics = response["metrics"]
            ml_signals = metrics.get("ml_signals")
            preprocessed = metrics.get("preprocessed")
            decision = metrics.get("decision")
            
            # ML Detector metrics with thresholds and status
            if ml_signals:
                ml_metrics = extract_ml_metrics(ml_signals, detector_config=payload.detector_config)
                
                # Policy metrics
                policy_metrics = PolicyMetrics(
                    matched_rule=decision.matched_rule if decision else None,
                    confidence=decision.confidence if decision else 0.5,
                    risk_level=get_risk_level(ml_signals)
                )
            
            # Preprocessing metrics
            if preprocessed:
                preprocessing_metrics = PreprocessingMetrics(
                    original_length=len(preprocessed.original_text),
                    normalized_length=len(preprocessed.normalized_text),
                    word_count=preprocessed.features.get("word_count", 0),
                    char_count=len(preprocessed.original_text)
                )
            
            # Latency breakdown
            latency_breakdown = {
                "preprocessing": metrics.get("preprocessing_latency_ms", 0),
                "ml_analysis": ml_signals.latency_ms if ml_signals else 0,
                "policy_eval": metrics.get("policy_latency_ms", 0),
                "backend": response.get("backend_latency_ms", 0)
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
                detector_config=payload.detector_config
            )
            
            # Add to metrics manager
            request_event = RequestEvent(**event)
            metrics_manager.add_request(request_event)
            
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

    except ContentBlockedException as e:
        # Blocked by policies
        total_latency = (time.time() - request_start_time) * 1000
        logger.warning(f"[{request_id}] Blocked by policies: {e.reason}")
        
        # Extract metrics even when blocked
        ml_metrics = []
        preprocessing_metrics = None
        policy_metrics = None
        latency_breakdown = {}
        
        if hasattr(e, 'ml_signals') and e.ml_signals:
            ml_signals = e.ml_signals
            
            # ML Detector metrics
            ml_metrics = extract_ml_metrics(ml_signals, detector_config=payload.detector_config)
            
            # Policy metrics
            policy_metrics = PolicyMetrics(
                matched_rule=e.details.get("matched_rule"),
                confidence=e.details.get("confidence", 0.9),
                risk_level=get_risk_level(ml_signals)
            )
            
            # Latency breakdown
            latency_breakdown = {
                "preprocessing": 0,  # Not available in exception
                "ml_analysis": ml_signals.latency_ms,
                "policy_eval": 0,
                "backend": 0
            }
        
        if hasattr(e, 'preprocessed') and e.preprocessed:
            preprocessing_metrics = PreprocessingMetrics(
                original_length=len(e.preprocessed.original_text),
                normalized_length=len(e.preprocessed.normalized_text),
                word_count=e.preprocessed.features.get("word_count", 0),
                char_count=len(e.preprocessed.original_text)
            )
        
        # Create standardized event for blocked request and broadcast
        if ml_signals:
            event = create_standardized_event(
                request_id=request_id,
                prompt=payload.message,
                response=e.reason,
                blocked=True,
                ml_signals=ml_signals,
                preprocessed=e.preprocessed if hasattr(e, 'preprocessed') else None,
                decision=type('obj', (object,), {'matched_rule': e.details.get("matched_rule")})(),
                latency_breakdown=latency_breakdown,
                total_latency=total_latency,
                session_id=None,  # TODO: Add session tracking
                detector_config=payload.detector_config
            )
            
            # Add to metrics manager
            request_event = RequestEvent(**event)
            metrics_manager.add_request(request_event)
            
            # Broadcast to WebSocket clients
            if event_queue:
                await event_queue.put(event)
        
        return ChatResponse(
            blocked=True,
            reason=e.reason,
            ml_detectors=ml_metrics,
            preprocessing=preprocessing_metrics,
            policy=policy_metrics,
            latency_breakdown=latency_breakdown,
            total_latency_ms=total_latency,
        )

    except BackendError as e:
        # Backend error
        logger.error(f"[{request_id}] Backend error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with the backend: {e.message}",
        ) from e

    except FirewallException as e:
        # General firewall error
        logger.error(f"[{request_id}] Firewall error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal firewall error: {e.message}",
        ) from e

    except Exception as e:
        # Unexpected error
        logger.exception(f"[{request_id}] Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "semantic-firewall"}


@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.
    
    Sends:
    - Real-time request events as they are processed
    - Periodic heartbeat pings
    
    Expects:
    - Pong responses to heartbeat pings
    """
    await manager.connect(websocket)
    
    # Start heartbeat task
    heartbeat_task = asyncio.create_task(manager.heartbeat_sender(websocket))
    
    try:
        while True:
            # Listen for messages from client (mainly pong responses)
            data = await websocket.receive_json()
            
            if data.get("type") == "pong":
                # Client responded to heartbeat
                logger.debug("Received pong from dashboard client")
            
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected")
        manager.disconnect(websocket)
        heartbeat_task.cancel()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        heartbeat_task.cancel()


@app.get("/api/stats")
async def get_stats():
    """
    Get executive KPIs and aggregated statistics.
    
    Returns:
        Dictionary with:
        - Total prompts
        - Percentage breakdowns (benign, suspicious, malicious)
        - Block/allow ratio
        - Prompts per minute
        - Risk trend
        - Average latencies
        - Risk category breakdown
    """
    try:
        stats = metrics_manager.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving statistics"
        )


@app.get("/api/models/available")
async def get_available_models():
    """
    Get list of available detector models for each category.
    
    Returns:
        Dictionary with available models for:
        - prompt_injection
        - pii
        - toxicity
        
        And default models for each category.
    """
    try:
        from fast_ml_filter.detector_factory import DetectorFactory
        
        available = DetectorFactory.get_available_models()
        defaults = DetectorFactory.get_default_models()
        
        return {
            "available": available,
            "defaults": defaults
        }
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving available models"
        )


@app.get("/api/models/cache")
async def get_models_cache_status():
    """
    Get status of the detector cache.
    
    Returns:
        Dictionary with:
        - cached_detectors: List of detector keys currently in cache
        - cache_size: Number of detectors in cache
        - cache_enabled: Whether caching is enabled
    """
    try:
        from fast_ml_filter.detector_factory import DetectorFactory
        
        # Create a factory instance to access cache
        factory = DetectorFactory()
        cache_stats = factory.get_cache_stats()
        
        return cache_stats
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving cache status"
        )


@app.post("/api/models/cache/clear")
async def clear_models_cache():
    """
    Clear the detector cache.
    
    Returns:
        Number of detectors removed from cache
    """
    try:
        from fast_ml_filter.detector_factory import DetectorFactory
        
        # Create a factory instance to access cache
        factory = DetectorFactory()
        count = factory.clear_cache()
        
        return {
            "message": f"Cache cleared successfully",
            "detectors_removed": count
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error clearing cache"
        )


@app.get("/api/recent-requests")
async def get_recent_requests(limit: int = 50):
    """
    Get the most recent N requests.
    
    Args:
        limit: Maximum number of requests to return (default: 50, max: 200)
        
    Returns:
        List of recent request events
    """
    try:
        # Limit to max 200
        limit = min(limit, 200)
        recent = metrics_manager.get_recent(limit=limit)
        return {"requests": recent, "count": len(recent)}
    except Exception as e:
        logger.error(f"Error getting recent requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving recent requests"
        )


@app.get("/api/session-analytics")
async def get_session_analytics(top: int = 5):
    """
    Get analytics for top sessions with most suspicious activity.
    
    Args:
        top: Number of top sessions to return (default: 5)
        
    Returns:
        List of session analytics
    """
    try:
        analytics = metrics_manager.get_session_analytics(top_n=top)
        return {"sessions": analytics, "count": len(analytics)}
    except Exception as e:
        logger.error(f"Error getting session analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving session analytics"
        )


@app.get("/api/temporal-breakdown")
async def get_temporal_breakdown(minutes: int = 10):
    """
    Get temporal breakdown of risk categories.
    
    Args:
        minutes: Number of minutes to analyze (default: 10, max: 60)
        
    Returns:
        Temporal breakdown with timestamps and category counts
    """
    try:
        minutes = min(minutes, 60)
        breakdown = metrics_manager.get_temporal_breakdown(minutes=minutes)
        return breakdown
    except Exception as e:
        logger.error(f"Error getting temporal breakdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving temporal breakdown"
        )


# ==================== Benchmark Endpoints ====================

class BenchmarkStartRequest(BaseModel):
    """Request to start a new benchmark."""
    dataset_name: str
    dataset_split: str = "test"
    max_samples: Optional[int] = None
    tenant_id: str = "benchmark"
    detector_config: Optional[dict[str, str]] = None


@app.on_event("startup")
async def initialize_benchmark_system():
    """Initialize benchmark database and runner on startup."""
    global benchmark_database, benchmark_runner
    
    try:
        benchmark_database = BenchmarkDatabase(BENCHMARK_DB_PATH)
        await benchmark_database.initialize()
        
        # Get orchestrator from container
        #orchestrator = container.orchestrator()
        benchmark_runner = BenchmarkRunner(firewall, benchmark_database)
        
        logger.info(f"Benchmark system initialized with database at {BENCHMARK_DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize benchmark system: {e}")
        # Don't fail the entire app if benchmarks fail to initialize
        benchmark_database = None
        benchmark_runner = None


@app.post("/api/benchmarks/start")
async def start_benchmark(request: BenchmarkStartRequest):
    """
    Start a new benchmark run.
    
    Args:
        request: Benchmark configuration
        
    Returns:
        Benchmark run ID and initial status
    """
    if not benchmark_runner:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Benchmark system not initialized"
        )
    
    try:
        run_id = await benchmark_runner.start_benchmark(
            dataset_name=request.dataset_name,
            dataset_split=request.dataset_split,
            max_samples=request.max_samples,
            tenant_id=request.tenant_id,
            model_config=request.detector_config
        )
        
        return {
            "run_id": run_id,
            "status": "running",
            "message": "Benchmark started successfully"
        }
    except Exception as e:
        logger.error(f"Error starting benchmark: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start benchmark: {str(e)}"
        )


@app.get("/api/benchmarks/status/{run_id}")
async def get_benchmark_status(run_id: str):
    """
    Get the current status of a benchmark run.
    
    Args:
        run_id: Benchmark run identifier
        
    Returns:
        Current status and progress information
    """
    if not benchmark_runner:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Benchmark system not initialized"
        )
    
    try:
        status_info = benchmark_runner.get_status(run_id)
        
        if not status_info:
            # Check database for completed/failed runs
            run_info = await benchmark_database.get_run(run_id)
            if not run_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Benchmark run not found"
                )
            
            # Parse config_snapshot to get detector_config
            import json
            config_snapshot = {}
            if run_info.get("config_snapshot"):
                try:
                    config_snapshot = json.loads(run_info["config_snapshot"])
                except:
                    config_snapshot = {}
            
            return {
                "run_id": run_id,
                "status": run_info["status"],
                "total_samples": run_info["total_samples"],
                "processed_samples": run_info["processed_samples"],
                "progress_percent": (run_info["processed_samples"] / run_info["total_samples"] * 100) 
                    if run_info["total_samples"] > 0 else 0,
                "detector_config": config_snapshot.get("detector_config")
            }
        
        # Add detector_config to status_info if available
        run_info = await benchmark_database.get_run(run_id)
        if run_info and run_info.get("config_snapshot"):
            import json
            try:
                config_snapshot = json.loads(run_info["config_snapshot"])
                status_info["detector_config"] = config_snapshot.get("detector_config")
            except:
                pass
        
        return status_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting benchmark status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving benchmark status"
        )


@app.post("/api/benchmarks/cancel/{run_id}")
async def cancel_benchmark(run_id: str):
    """
    Cancel a running benchmark.
    
    Args:
        run_id: Benchmark run identifier
        
    Returns:
        Cancellation status
    """
    if not benchmark_runner:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Benchmark system not initialized"
        )
    
    try:
        success = await benchmark_runner.cancel_benchmark(run_id)
        
        if success:
            return {"message": "Benchmark cancelled successfully"}
        else:
            return {"message": "Benchmark not found or already completed"}
    except Exception as e:
        logger.error(f"Error cancelling benchmark: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cancelling benchmark"
        )


@app.get("/api/benchmarks/runs")
async def get_benchmark_runs(limit: int = 50, offset: int = 0):
    """
    Get list of all benchmark runs with pagination.
    
    Args:
        limit: Maximum number of runs to return
        offset: Number of runs to skip
        
    Returns:
        List of benchmark runs
    """
    if not benchmark_database:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Benchmark system not initialized"
        )
    
    try:
        runs = await benchmark_database.get_all_runs(limit=limit, offset=offset)
        return {"runs": runs, "count": len(runs)}
    except Exception as e:
        logger.error(f"Error getting benchmark runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving benchmark runs"
        )


@app.get("/api/benchmarks/results/{run_id}")
async def get_benchmark_results(
    run_id: str,
    result_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get detailed results for a benchmark run.
    
    Args:
        run_id: Benchmark run identifier
        result_type: Optional filter (TRUE_POSITIVE, FALSE_POSITIVE, TRUE_NEGATIVE, FALSE_NEGATIVE)
        limit: Maximum number of results to return
        offset: Number of results to skip
        
    Returns:
        List of benchmark results
    """
    if not benchmark_database:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Benchmark system not initialized"
        )
    
    try:
        results = await benchmark_database.get_results(
            run_id=run_id,
            result_type=result_type,
            limit=limit,
            offset=offset
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error getting benchmark results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving benchmark results"
        )


@app.get("/api/benchmarks/metrics/{run_id}")
async def get_benchmark_metrics(run_id: str):
    """
    Get calculated metrics for a benchmark run.
    
    Args:
        run_id: Benchmark run identifier
        
    Returns:
        Benchmark metrics including confusion matrix and performance stats
    """
    if not benchmark_database:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Benchmark system not initialized"
        )
    
    try:
        metrics = await benchmark_database.get_metrics(run_id)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Metrics not found for this run (may still be processing)"
            )
        
        # Add detector_config from run info
        run_info = await benchmark_database.get_run(run_id)
        if run_info and run_info.get("config_snapshot"):
            import json
            try:
                config_snapshot = json.loads(run_info["config_snapshot"])
                metrics["detector_config"] = config_snapshot.get("detector_config")
            except:
                pass
        
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting benchmark metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving benchmark metrics"
        )


@app.get("/api/benchmarks/errors/{run_id}")
async def get_benchmark_errors(run_id: str):
    """
    Get detailed error analysis (false positives and false negatives).
    
    Args:
        run_id: Benchmark run identifier
        
    Returns:
        Error analysis with false positives and false negatives
    """
    if not benchmark_database:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Benchmark system not initialized"
        )
    
    try:
        error_analysis = await benchmark_database.get_error_analysis(run_id)
        return error_analysis
    except Exception as e:
        logger.error(f"Error getting benchmark error analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving error analysis"
        )


@app.get("/api/benchmarks/datasets")
async def get_available_datasets():
    """
    Get list of available predefined datasets.
    
    Returns:
        List of datasets with metadata
    """
    try:
        loader = DatasetLoader()
        datasets = loader.get_available_datasets()
        return {"datasets": datasets, "count": len(datasets)}
    except Exception as e:
        logger.error(f"Error getting available datasets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving available datasets"
        )
