import logging
import os
import uuid

from container import FirewallContainer
from core.analyzer import FirewallAnalyzer
from core.backend_proxy import BackendProxyService
from core.exceptions import (BackendError, ContentBlockedException,
                             FirewallException)
from core.orchestrator import FirewallOrchestrator
from fast_ml_filter.ml_filter_service import MLSignals
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
