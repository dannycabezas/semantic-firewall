import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import List

from container import FirewallContainer
from core.analyzer import FirewallAnalyzer
from core.backend_proxy import BackendProxyService
from core.exceptions import (BackendError, ContentBlockedException,
                             FirewallException)
from core.orchestrator import FirewallOrchestrator
from fast_ml_filter.ml_filter_service import MLSignals
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from metrics_manager import MetricsManager, RequestEvent
from pydantic import BaseModel

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


def create_firewall_orchestrator() -> FirewallOrchestrator:
    """Factory to create the firewall orchestrator."""
    analyzer = FirewallAnalyzer(
        preprocessor=container.preprocessor_service(),
        ml_filter=container.ml_filter_service(),
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
    session_id: str = None
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
    }
    
    return event


def extract_ml_metrics(ml_signals: MLSignals) -> list[DetectorMetrics]:
    """Extract ML detector metrics with thresholds and status."""
    # Thresholds from policies.rego
    thresholds = {
        "pii": 0.8,
        "toxicity": 0.7,
        "prompt_injection": 0.8,
        "heuristic": 1.0
    }
    
    metrics = []
    
    if hasattr(ml_signals, 'pii_metrics') and ml_signals.pii_metrics:
        metrics.append(DetectorMetrics(
            name="PII Detector",
            score=ml_signals.pii_metrics.score,
            latency_ms=ml_signals.pii_metrics.latency_ms,
            threshold=thresholds["pii"],
            status=get_status(ml_signals.pii_metrics.score, thresholds["pii"])
        ))
    
    if hasattr(ml_signals, 'toxicity_metrics') and ml_signals.toxicity_metrics:
        metrics.append(DetectorMetrics(
            name="Toxicity Detector",
            score=ml_signals.toxicity_metrics.score,
            latency_ms=ml_signals.toxicity_metrics.latency_ms,
            threshold=thresholds["toxicity"],
            status=get_status(ml_signals.toxicity_metrics.score, thresholds["toxicity"])
        ))
    
    if hasattr(ml_signals, 'prompt_injection_metrics') and ml_signals.prompt_injection_metrics:
        metrics.append(DetectorMetrics(
            name="Prompt Injection Detector",
            score=ml_signals.prompt_injection_metrics.score,
            latency_ms=ml_signals.prompt_injection_metrics.latency_ms,
            threshold=thresholds["prompt_injection"],
            status=get_status(ml_signals.prompt_injection_metrics.score, thresholds["prompt_injection"])
        ))
    
    if hasattr(ml_signals, 'heuristic_metrics') and ml_signals.heuristic_metrics:
        heuristic_score = ml_signals.heuristic_metrics.score
        metrics.append(DetectorMetrics(
            name="Heuristic Detector",
            score=heuristic_score,
            latency_ms=ml_signals.heuristic_metrics.latency_ms,
            threshold=thresholds["heuristic"],
            status="block" if heuristic_score >= 1.0 else "pass"
        ))
    
    return metrics


# === ENDPOINTS ===
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest) -> ChatResponse:
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
    
    request_id = generate_request_id()
    request_start_time = time.time()
    logger.info(f"[{request_id}] New chat request: {payload.message[:50]}...")

    try:
        # Process complete request through the orchestrator
        response = await firewall.process_chat_request(
            message=payload.message,
            request_id=request_id,
            analyze_egress=False,
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
                ml_metrics = extract_ml_metrics(ml_signals)
                
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
                session_id=None  # TODO: Add session tracking
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
            ml_metrics = extract_ml_metrics(ml_signals)
            
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
                session_id=None  # TODO: Add session tracking
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
