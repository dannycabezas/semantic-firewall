import logging
import os
import uuid

from container import FirewallContainer
from core.analyzer import AnalysisDirection, FirewallAnalyzer
from core.backend_proxy import BackendProxyService
from core.exceptions import (BackendError, ContentBlockedException,
                             FirewallException)
from core.orchestrator import FirewallOrchestrator
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
    """Métricas de un detector individual."""
    name: str
    score: float
    latency_ms: float

class ChatResponse(BaseModel):

    blocked: bool = False
    reason: str | None = None
    reply: str | None = None
    # Nuevas métricas
    ml_detectors: list[DetectorMetrics] | None = None
    total_latency_ms: float | None = None
    analysis_latency_ms: float | None = None
    backend_latency_ms: float | None = None


class ChatRequest(BaseModel):

    message: str


def generate_request_id() -> str:
    return str(uuid.uuid4())


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
        
        # Extraer métricas de los detectores ML
        ml_metrics = []
        analysis_latency = 0
        if "metrics" in response:
            metrics = response["metrics"]
            ml_signals = metrics.get("ml_signals")
            if ml_signals:
                if hasattr(ml_signals, 'pii_metrics') and ml_signals.pii_metrics:
                    ml_metrics.append(DetectorMetrics(
                        name="PII Detector",
                        score=ml_signals.pii_metrics.score,
                        latency_ms=ml_signals.pii_metrics.latency_ms
                    ))
                if hasattr(ml_signals, 'toxicity_metrics') and ml_signals.toxicity_metrics:
                    ml_metrics.append(DetectorMetrics(
                        name="Toxicity Detector",
                        score=ml_signals.toxicity_metrics.score,
                        latency_ms=ml_signals.toxicity_metrics.latency_ms
                    ))
                if hasattr(ml_signals, 'prompt_injection_metrics') and ml_signals.prompt_injection_metrics:
                    ml_metrics.append(DetectorMetrics(
                        name="Prompt Injection Detector",
                        score=ml_signals.prompt_injection_metrics.score,
                        latency_ms=ml_signals.prompt_injection_metrics.latency_ms
                    ))
                if hasattr(ml_signals, 'heuristic_metrics') and ml_signals.heuristic_metrics:
                    ml_metrics.append(DetectorMetrics(
                        name="Heuristic Detector",
                        score=ml_signals.heuristic_metrics.score,
                        latency_ms=ml_signals.heuristic_metrics.latency_ms
                    ))
            
            analysis_latency = metrics.get("analysis_latency_ms", 0)

        return ChatResponse(
            blocked=False,
            reply=response.get("reply"),
            ml_detectors=ml_metrics,
            total_latency_ms=total_latency,
            analysis_latency_ms=analysis_latency,
            backend_latency_ms=response.get("backend_latency_ms"),
        )

    except ContentBlockedException as e:
        # Blocked by policies
        total_latency = (time.time() - request_start_time) * 1000
        logger.warning(f"[{request_id}] Blocked by policies: {e.reason}")
        
        # Obtener métricas incluso cuando está bloqueado
        ml_metrics = []
        if hasattr(e, 'ml_signals'):
            ml_signals = e.ml_signals
            if hasattr(ml_signals, 'pii_metrics') and ml_signals.pii_metrics:
                ml_metrics.append(DetectorMetrics(
                    name="PII Detector",
                    score=ml_signals.pii_metrics.score,
                    latency_ms=ml_signals.pii_metrics.latency_ms
                ))
            if hasattr(ml_signals, 'toxicity_metrics') and ml_signals.toxicity_metrics:
                ml_metrics.append(DetectorMetrics(
                    name="Toxicity Detector",
                    score=ml_signals.toxicity_metrics.score,
                    latency_ms=ml_signals.toxicity_metrics.latency_ms
                ))
            if hasattr(ml_signals, 'prompt_injection_metrics') and ml_signals.prompt_injection_metrics:
                ml_metrics.append(DetectorMetrics(
                    name="Prompt Injection Detector",
                    score=ml_signals.prompt_injection_metrics.score,
                    latency_ms=ml_signals.prompt_injection_metrics.latency_ms
                ))
            if hasattr(ml_signals, 'heuristic_metrics') and ml_signals.heuristic_metrics:
                ml_metrics.append(DetectorMetrics(
                    name="Heuristic Detector",
                    score=ml_signals.heuristic_metrics.score,
                    latency_ms=ml_signals.heuristic_metrics.latency_ms
                ))
        
        return ChatResponse(
            blocked=True,
            reason=e.reason,
            ml_detectors=ml_metrics,
            total_latency_ms=total_latency,
            analysis_latency_ms=e.details.get("latency_ms", 0),
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
