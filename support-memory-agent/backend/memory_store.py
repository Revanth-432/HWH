"""
memory_store.py
---------------
Thin wrapper around the *hindsight-client* SDK for the Customer Support
Memory Agent.  Uses the SDK's ``retain`` and ``recall`` methods to store
and retrieve per-customer interaction histories.

NOTE: The file is intentionally named ``memory_store.py`` (not
``hindsight_client.py``) to avoid shadowing the pip-installed
``hindsight_client`` package.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

HINDSIGHT_BASE_URL: str = os.getenv(
    "HINDSIGHT_BASE_URL",
    os.getenv("HINDSIGHT_API_URL", "http://localhost:8888"),
)
HINDSIGHT_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "")


class MemoryStore:
    """High-level memory façade backed by the Hindsight SDK."""

    def __init__(
        self,
        base_url: str = HINDSIGHT_BASE_URL,
        api_key: str = HINDSIGHT_API_KEY,
    ) -> None:
        self.client = Hindsight(base_url=base_url, api_key=api_key)

    # ------------------------------------------------------------------
    # Health / connectivity
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """Ping the Hindsight API and return its version info."""
        version = self.client.get_version()
        return {"status": "ok", "version": str(version)}

    # ------------------------------------------------------------------
    # remember_interaction  →  Hindsight SDK ``retain``
    # ------------------------------------------------------------------

    def remember_interaction(
        self,
        customer_id: str,
        channel: str,
        message: str,
        issue_summary: str,
        attempted_fix: str,
        resolution_status: str,
        sentiment: str,
        contact_count: int,
        timestamp: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Persist a single support interaction into the customer's memory bank.

        Uses the Hindsight SDK's ``retain`` method with ``customer_id`` as
        the ``bank_id``, so all interactions for a customer live in the same
        memory bank.
        """
        ts = timestamp or datetime.now(timezone.utc)

        # Build a rich text blob that Hindsight will chunk & index.
        content = (
            f"[Support Interaction — {channel.upper()}]\n"
            f"Timestamp: {ts.isoformat()}\n"
            f"Customer ID: {customer_id}\n"
            f"Channel: {channel}\n"
            f"Customer Message: {message}\n"
            f"Issue Summary: {issue_summary}\n"
            f"Attempted Fix: {attempted_fix}\n"
            f"Resolution Status: {resolution_status}\n"
            f"Customer Sentiment: {sentiment}\n"
            f"Contact Count (for this issue): {contact_count}\n"
        )

        metadata = {
            "channel": channel,
            "resolution_status": resolution_status,
            "sentiment": sentiment,
            "contact_count": str(contact_count),
            "issue_summary": issue_summary,
        }

        result = self.client.retain(
            bank_id=customer_id,
            content=content,
            timestamp=ts,
            context=f"Customer support interaction via {channel}",
            metadata=metadata,
            tags=tags or [channel, resolution_status, sentiment],
        )

        return {
            "status": "retained",
            "bank_id": customer_id,
            "items_count": getattr(result, "items_count", 1),
        }

    # ------------------------------------------------------------------
    # recall_context  →  Hindsight SDK ``recall``
    # ------------------------------------------------------------------

    def recall_context(
        self,
        customer_id: str,
        query: str = "all support interactions, issues, sentiment and resolution status",
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Fetch the interaction history for a customer from Hindsight.

        Returns a dict with:
        - ``results``: list of recalled memory texts
        - ``prompt_string``: a ready-to-inject prompt block
        - ``raw_response``: the full RecallResponse object
        """
        try:
            response = self.client.recall(
                bank_id=customer_id,
                query=query,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            # Bank may not exist yet — treat as empty history.
            return {"results": [], "prompt_string": "", "raw_response": None, "error": str(exc)}

        results = []
        for r in response.results or []:
            results.append({
                "text": r.text,
                "type": getattr(r, "type", None),
                "context": getattr(r, "context", None),
            })

        prompt_string = response.to_prompt_string() if response.results else ""

        return {
            "results": results,
            "prompt_string": prompt_string,
            "raw_response": response,
        }
