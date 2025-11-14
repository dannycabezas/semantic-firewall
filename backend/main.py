from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="SPG Test Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatIn(BaseModel):
    message: str


@app.post("/api/chat")
async def chat(payload: ChatIn):
    # Simulate an LLM/back-end response (echo + simple transform)
    msg = payload.message.strip()
    if not msg:
        return {"reply": "Please type something."}
    return {"reply": f"Echo: {msg}"}
