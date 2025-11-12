import os
import re
import time
import yaml
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

# Load config & rules at startup
with open("config.yaml", "r") as f:
    CFG = yaml.safe_load(f) or {}

with open("rules/prompt_injection_rules.yaml", "r") as f:
    RULES = yaml.safe_load(f) or {}

PATTERNS = [re.compile(pat, re.IGNORECASE) for pat in (RULES.get("patterns") or [])]
DENYLIST = [s.lower() for s in (RULES.get("denylist") or [])]

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


def log(msg: str):
    if LOG_LEVEL in ("debug", "info"):
        print(msg, flush=True)


def analyze_prompt(prompt: str) -> Decision:
    if len(prompt) > int(CFG.get("max_prompt_chars", 4000)):
        return Decision(blocked=True, reason="Prompt too long (size limit)")

    for rx in PATTERNS:
        if rx.search(prompt):
            return Decision(blocked=bool(CFG.get("block_on_match", True)), reason=f"Pattern match: {rx.pattern}")

    lower = prompt.lower()
    for needle in DENYLIST:
        if needle in lower:
            return Decision(blocked=True, reason=f"Contains denylisted token: {needle}")

    return Decision(blocked=False)


@app.post("/api/chat")
async def proxy_chat(payload: ChatIn):
    start = time.time()
    decision = analyze_prompt(payload.message)

    if decision.blocked:
        log(f"[BLOCK] reason={decision.reason}")
        return {"blocked": True, "reason": decision.reason}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(f"{BACKEND_URL}/api/chat", json={"message": payload.message})
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log(f"[ERROR] backend={BACKEND_URL} error={e}")
            return {"blocked": True, "reason": "Error contacting backend."}
    
    # OPTIONAL: analyze outbount content (egress filter)
    reply = (data or {}).get("reply", "")
    egress_decision = analyze_prompt(reply)
    if egress_decision.blocked:
        log(f"[BLOCK] reason={egress_decision.reason}")
        return {"blocked": True, "reason": egress_decision.reason}
    
    dt = (time.time() - start) * 1000
    log(f"[ALLOW] latency_ms={dt:.1f} ")
    return data