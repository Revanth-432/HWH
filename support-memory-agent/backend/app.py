"""
app.py
------
FastAPI application entry-point for the Customer Support Memory Agent.
Exposes REST endpoints consumed by the frontend dashboard.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory_store import MemoryStore
from llm_client import LLMClient
from memory_schema import Customer, Interaction, MemoryPayload
from agent import handle_customer_message, build_system_prompt

load_dotenv()

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Customer Support Memory Agent",
    description="AI-powered support agent with cross-channel memory via Hindsight.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_store = MemoryStore()
llm = LLMClient()

# ---------------------------------------------------------------------------
# Seed data loader
# ---------------------------------------------------------------------------

SEED_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_customers.json"


def load_seed_customers() -> List[Customer]:
    """Load and validate the synthetic seed-customer dataset."""
    if not SEED_DATA_PATH.exists():
        return []
    with open(SEED_DATA_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return [Customer(**c) for c in raw]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    customer_id: str
    channel: str = "chat"
    message: str
    memory_off: bool = False


class MessageRequest(BaseModel):
    """Pydantic model used by the /message endpoint."""
    customer_id: str
    channel: str = "chat"
    message: str
    memory_off: bool = False


class ChatResponse(BaseModel):
    customer_id: str
    channel: str
    reply: str
    memory_used: bool
    memory_results_count: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"status": "ok", "service": "support-memory-agent"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/customers", response_model=List[Customer])
async def list_customers():
    """Return all seed customers (later: query Hindsight)."""
    return load_seed_customers()


@app.get("/customers/{email}")
def get_customer(email: str):
    """Look up a single customer by email (the cross-channel ID)."""
    customers = load_seed_customers()
    for c in customers:
        if c.email == email:
            return c
    raise HTTPException(status_code=404, detail="Customer not found")


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """Handle an incoming customer message through the memory-aware agent."""
    result = handle_customer_message(
        customer_id=req.customer_id,
        channel=req.channel,
        message=req.message,
        memory_off=req.memory_off,
        memory_store=memory_store,
        llm=llm,
    )
    return ChatResponse(
        customer_id=result["customer_id"],
        channel=result["channel"],
        reply=result["reply"],
        memory_used=result["memory_used"],
        memory_results_count=result["memory_results_count"],
    )


@app.post("/message")
def message_endpoint(req: MessageRequest):
    """Phase 2 endpoint: handle a customer message and return the LLM reply.

    This is the primary endpoint used by the frontend chat UI.
    """
    result = handle_customer_message(
        customer_id=req.customer_id,
        channel=req.channel,
        message=req.message,
        memory_off=req.memory_off,
        memory_store=memory_store,
        llm=llm,
    )
    return {
        "customer_id": result["customer_id"],
        "channel": result["channel"],
        "reply": result["reply"],
        "memory_used": result["memory_used"],
        "memory_results_count": result["memory_results_count"],
    }


@app.get("/customers/{customer_id}/history")
def customer_history(customer_id: str):
    """Phase 2 endpoint: return the raw Hindsight memory for the transparency panel.

    Calls recall_context() and strips the non-serialisable raw_response before
    returning the payload to the frontend.
    """
    context = memory_store.recall_context(customer_id)
    # Drop the raw SDK response object — it's not JSON-serialisable.
    context.pop("raw_response", None)
    return context


@app.post("/summarise/{email}")
def summarise_customer(email: str):
    """Generate an LLM summary of a customer's interaction history."""
    customers = load_seed_customers()
    target = next((c for c in customers if c.email == email), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    interactions_json = json.dumps(
        [i.model_dump(mode="json") for i in target.interactions], indent=2
    )
    summary = llm.summarise_interactions(interactions_json)
    return {"customer_id": email, "summary": summary}


@app.post("/escalate/{email}")
def check_escalation(email: str):
    """Assess whether a customer's ticket should be escalated."""
    customers = load_seed_customers()
    target = next((c for c in customers if c.email == email), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    interactions_json = json.dumps(
        [i.model_dump(mode="json") for i in target.interactions], indent=2
    )
    summary = llm.summarise_interactions(interactions_json)
    assessment = llm.assess_escalation(summary)
    return {
        "customer_id": email,
        "summary": summary,
        "escalation_assessment": assessment,
    }


# ---------------------------------------------------------------------------
# Dev server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )
