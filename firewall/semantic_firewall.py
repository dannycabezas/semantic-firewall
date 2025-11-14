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


class ChatRequest(BaseModel):

    message: str


class ChatResponse(BaseModel):

    blocked: bool = False
    reason: str | None = None
    reply: str | None = None


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
        Backend response or block message

    Raises:
        HTTPException: En caso de error
    """
    request_id = generate_request_id()
    logger.info(f"[{request_id}] New chat request: {payload.message[:50]}...")

    try:
        # Process complete request through the orchestrator
        response = await firewall.process_chat_request(
            message=payload.message,
            request_id=request_id,
            analyze_egress=False,
        )

        return ChatResponse(
            blocked=False,
            reply=response.get("reply"),
        )

    except ContentBlockedException as e:
        # Blocked by policies
        logger.warning(f"[{request_id}] Blocked by policies: {e.reason}")
        return ChatResponse(
            blocked=True,
            reason=e.reason,
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
