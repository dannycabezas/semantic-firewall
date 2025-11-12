"""Semantic Firewall - Main application with integrated components."""

import os
import time
import uuid
import httpx
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from container import FirewallContainer

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

# Load config
with open("config.yaml", "r") as f:
    CFG = yaml.safe_load(f) or {}

# Initialize dependency injection container
container = FirewallContainer()
container.config.from_dict(CFG)

app = FastAPI(title="SPG Semantic Firewall")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatIn(BaseModel):
    message: str

class Decision(BaseModel):
    blocked: bool
    reason: str | None = None


def generate_request_id() -> str:
    """Generate unique request ID."""
    return str(uuid.uuid4())


@app.post("/api/chat")
async def proxy_chat(payload: ChatIn):
    """
    Main chat endpoint with integrated firewall components.
    
    Flow:
    1. Preprocess (normalize, vectorize, extract features)
    2. Fast ML Filter (PII, toxicity, heuristics)
    3. Policy Engine (evaluate policies)
    4. Action Orchestrator (log, alert, etc.)
    5. Decision: block or allow (proxy to backend)
    """
    start = time.time()
    request_id = generate_request_id()
    
    # Get services from container
    preprocessor = container.preprocessor_service()
    ml_filter = container.ml_filter_service()
    policy_engine = container.policy_service()
    orchestrator = container.orchestrator_service()
    
    try:
        # 1. Preprocess
        preprocessed = preprocessor.preprocess(payload.message, store=False)
        
        # 2. Fast ML Filter
        ml_signals = ml_filter.analyze(preprocessed.normalized_text)
        
        # 3. Policy Engine
        decision = policy_engine.evaluate(
            ml_signals=ml_signals,
            features=preprocessed.features,
            tenant_id="default"  # Can be extracted from request headers
        )
        
        # 4. Action Orchestrator
        orchestrator.execute(
            decision=decision,
            request_id=request_id,
            context={
                "timestamp": time.time(),
                "message_length": len(payload.message),
                "latency_ms": ml_signals.latency_ms
            }
        )
        
        # 5. Decision: block or allow
        if decision.blocked:
            return {"blocked": True, "reason": decision.reason}
        
        # Allow: proxy to backend
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                r = await client.post(
                    f"{BACKEND_URL}/api/chat",
                    json={"message": payload.message}
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                orchestrator.logger.log(
                    "error",
                    f"Backend error: {e}",
                    backend_url=BACKEND_URL
                )
                return {"blocked": True, "reason": "Error contacting backend."}
        
        # Optional: analyze outbound content (egress filter)
        reply = (data or {}).get("reply", "")
        if reply:
            # Preprocess reply
            reply_preprocessed = preprocessor.preprocess(reply, store=False)
            reply_ml_signals = ml_filter.analyze(reply_preprocessed.normalized_text)
            reply_decision = policy_engine.evaluate(
                ml_signals=reply_ml_signals,
                features=reply_preprocessed.features,
                tenant_id="default"
            )
            
            if reply_decision.blocked:
                orchestrator.execute(
                    decision=reply_decision,
                    request_id=f"{request_id}_egress",
                    context={
                        "timestamp": time.time(),
                        "direction": "egress"
                    }
                )
                return {"blocked": True, "reason": reply_decision.reason}
        
        dt = (time.time() - start) * 1000
        orchestrator.logger.log(
            "info",
            f"Request allowed - latency: {dt:.1f}ms",
            request_id=request_id,
            latency_ms=dt
        )
        
        return data
        
    except Exception as e:
        # Error handling
        orchestrator.logger.log(
            "error",
            f"Firewall error: {e}",
            request_id=request_id,
            error=str(e)
        )
        return {"blocked": True, "reason": "Internal firewall error."}
