"""
memory_schema.py
----------------
Pydantic models defining the shape of customer interaction memories
stored in Hindsight. These schemas enforce consistency across all
channels (chat, email, phone) and make it easy to validate data
before writing to the memory store.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Channel(str, Enum):
    """Communication channel through which the interaction occurred."""
    CHAT = "chat"
    EMAIL = "email"
    PHONE = "phone"


class ResolutionStatus(str, Enum):
    """Current resolution state of a support interaction."""
    OPEN = "open"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class SentimentLabel(str, Enum):
    """Coarse sentiment bucket derived from the customer's message."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------

class Interaction(BaseModel):
    """A single support interaction record."""

    interaction_id: str = Field(
        ...,
        description="Unique identifier for this interaction (UUID recommended).",
    )
    channel: Channel
    timestamp: datetime
    message: str = Field(
        ...,
        description="The customer's original message or call transcript summary.",
    )
    attempted_fix: str = Field(
        ...,
        description="What the support agent tried in order to resolve the issue.",
    )
    resolution_status: ResolutionStatus
    agent_name: Optional[str] = Field(
        None,
        description="Name of the support agent who handled the interaction.",
    )
    sentiment: Optional[SentimentLabel] = None
    tags: List[str] = Field(
        default_factory=list,
        description="Free-form tags for categorisation (e.g. 'billing', 'bug').",
    )


class Customer(BaseModel):
    """
    Top-level customer record.
    The *email* field doubles as a stable ``customer_id`` that remains
    consistent across chat, email, and phone channels.
    """

    name: str
    email: EmailStr = Field(
        ...,
        description="Primary email — also used as the cross-channel customer_id.",
    )
    interactions: List[Interaction] = Field(default_factory=list)


class MemoryPayload(BaseModel):
    """
    Wrapper sent to the Hindsight memory store when persisting or
    querying customer context.
    """

    customer_id: str = Field(
        ...,
        description="The customer's email address (stable cross-channel ID).",
    )
    context_summary: str = Field(
        ...,
        description="LLM-generated summary of past interactions for this customer.",
    )
    interaction_count: int = 0
    has_unresolved_issues: bool = False
    escalation_recommended: bool = False
    recent_interactions: List[Interaction] = Field(default_factory=list)
