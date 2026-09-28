"""
agent.py
--------
Orchestration logic for the Customer Support Memory Agent.

Builds context-aware system prompts using Hindsight memory, sends messages
through the LLM, and persists new interactions back to the memory store.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from dotenv import load_dotenv

from memory_store import MemoryStore
from llm_client import LLMClient

load_dotenv()

# Shared singletons (created once, reused across calls).
_memory_store = MemoryStore()
_llm = LLMClient()


# ---------------------------------------------------------------------------
# Keyword-based heuristic extraction
# ---------------------------------------------------------------------------

def _extract_issue_summary(reply: str, user_message: str) -> str:
    """Pull a one-line issue summary from the LLM reply or the user message."""
    # If the reply mentions an issue, use the first sentence.
    first_sentence = reply.split(".")[0].strip()
    if len(first_sentence) > 15:
        return first_sentence[:200]
    return user_message[:200]


def _extract_attempted_fix(reply: str) -> str:
    """Guess the fix from the reply using keyword patterns."""
    fix_patterns = [
        r"(?:I(?:'ve| have|'ll| will)|[Ww]e(?:'ve| have|'ll| will)|[Ll]et me)\s+(.+?)(?:\.|$)",
        r"(?:[Pp]lease try|[Yy]ou can|[Hh]ere'?s? (?:what|how))\s+(.+?)(?:\.|$)",
    ]
    for pattern in fix_patterns:
        match = re.search(pattern, reply)
        if match:
            return match.group(0).strip()[:300]
    # Fall back to the whole reply truncated.
    return reply[:300]


def _extract_resolution_status(reply: str) -> str:
    """Determine the resolution status from the reply content."""
    reply_lower = reply.lower()
    if any(kw in reply_lower for kw in ["escalat", "senior agent", "supervisor", "manager"]):
        return "escalated"
    if any(kw in reply_lower for kw in ["resolved", "fixed", "solution", "that should fix"]):
        return "resolved"
    return "open"


def _extract_sentiment(user_message: str) -> str:
    """Rough sentiment classification from the user's message."""
    msg = user_message.lower()
    if any(kw in msg for kw in ["frustrat", "angry", "unacceptable", "furious", "disgusted", "worst"]):
        return "frustrated"
    if any(kw in msg for kw in ["thank", "great", "awesome", "love", "happy", "pleased"]):
        return "positive"
    if any(kw in msg for kw in ["problem", "issue", "error", "fail", "broken", "not working", "bug"]):
        return "negative"
    return "neutral"


def _estimate_contact_count(memory_context: Dict[str, Any]) -> int:
    """Count how many prior interactions we have in memory for this customer."""
    results = memory_context.get("results", [])
    return len(results) + 1  # +1 for the current message


# ---------------------------------------------------------------------------
# System-prompt builder
# ---------------------------------------------------------------------------

BASE_SYSTEM_PROMPT = """\
You are a friendly, professional customer-support agent for a SaaS company.
Your name is "SupportBot".  Be empathetic, concise, and solution-oriented.
Always greet the customer by name when you know it.\
"""

ESCALATION_RULE = """
🚨 CRITICAL ESCALATION RULE 🚨
The memory shows that this customer has contacted support multiple times about the SAME unresolved issue. 
(System Note: We retrieved {contact_count} memory facts, but this is NOT the number of contacts. You must look strictly inside the facts for the specific 'contact count' phrase to find the true number of times they reached out).

You MUST NOT attempt another fix.
Instead, you MUST:
  1. Sincerely apologise for the repeated inconvenience.
  2. Explicitly tell the customer that you are NOW escalating their case
     to a **senior support agent / supervisor** who will personally handle it.
  3. Provide a reference summary of the issue so the senior agent has context.
Do NOT suggest workarounds, do NOT ask the customer to try anything else.\
"""


def build_system_prompt(
    customer_id: str,
    memory_off: bool = False,
    *,
    memory_store: Optional[MemoryStore] = None,
) -> tuple[str, Dict[str, Any]]:
    """Build a system prompt, optionally enriched with recalled memory.

    Returns:
        (system_prompt, memory_context_dict)
    """
    store = memory_store or _memory_store

    if memory_off:
        return (BASE_SYSTEM_PROMPT, {"results": []})

    # Recall everything we know about this customer.
    memory_context = store.recall_context(customer_id)
    prompt_parts = [BASE_SYSTEM_PROMPT]

    results = memory_context.get("results", [])
    if results:
        prompt_string = memory_context.get("prompt_string", "")
        prompt_parts.append(
            f"\n--- CUSTOMER MEMORY (customer_id: {customer_id}) ---\n"
            f"The following is the recalled interaction history for this customer:\n\n"
            f"{prompt_string}\n"
            f"--- END CUSTOMER MEMORY ---"
        )

        # Count contacts about open/unresolved issues.
        contact_count = len(results)
        open_count = 0
        for r in results:
            text = r.get("text", "").lower()
            if "open" in text or "escalated" in text or "unresolved" in text:
                open_count += 1

        if open_count >= 3 or contact_count >= 3:
            prompt_parts.append(
                ESCALATION_RULE.format(contact_count=max(contact_count, open_count))
            )

    system_prompt = "\n\n".join(prompt_parts)
    return (system_prompt, memory_context)


# ---------------------------------------------------------------------------
# Main message handler
# ---------------------------------------------------------------------------

def handle_customer_message(
    customer_id: str,
    channel: str,
    message: str,
    memory_off: bool = False,
    *,
    memory_store: Optional[MemoryStore] = None,
    llm: Optional[LLMClient] = None,
) -> Dict[str, Any]:
    """Process an incoming customer message end-to-end.

    1. Build a system prompt (with or without memory).
    2. Call the LLM for a reply.
    3. If memory is ON, persist the new interaction to Hindsight.

    Returns a dict with the reply and metadata.
    """
    store = memory_store or _memory_store
    llm_client = llm or _llm

    # 1 — Build prompt
    system_prompt, memory_context = build_system_prompt(
        customer_id, memory_off=memory_off, memory_store=store,
    )

    # 2 — Get LLM reply
    reply = llm_client.get_reply(system_prompt=system_prompt, user_message=message)

    # 3 — Persist to memory (only when memory is ON)
    retain_result = None
    if not memory_off:
        issue_summary = _extract_issue_summary(reply, message)
        attempted_fix = _extract_attempted_fix(reply)
        resolution_status = _extract_resolution_status(reply)
        sentiment = _extract_sentiment(message)
        contact_count = _estimate_contact_count(memory_context)

        try:
            retain_result = store.remember_interaction(
                customer_id=customer_id,
                channel=channel,
                message=message,
                issue_summary=issue_summary,
                attempted_fix=attempted_fix,
                resolution_status=resolution_status,
                sentiment=sentiment,
                contact_count=contact_count,
            )
        except Exception as exc:
            print(f"[Agent] Warning — failed to retain interaction: {exc}")

    return {
        "customer_id": customer_id,
        "channel": channel,
        "reply": reply,
        "memory_used": not memory_off,
        "memory_results_count": len(memory_context.get("results", [])),
        "retain_result": retain_result,
    }
