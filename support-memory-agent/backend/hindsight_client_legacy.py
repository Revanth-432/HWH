"""
hindsight_client.py
-------------------
Thin wrapper around the Hindsight memory-store API.
Handles authentication, CRUD operations on customer memories,
and translates responses into our Pydantic schemas.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

HINDSIGHT_API_URL: str = os.getenv("HINDSIGHT_BASE_URL", os.getenv("HINDSIGHT_API_URL", "http://localhost:8888"))
HINDSIGHT_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "")


class HindsightClient:
    """Minimal client for the Hindsight memory API."""

    def __init__(
        self,
        base_url: str = HINDSIGHT_API_URL,
        api_key: str = HINDSIGHT_API_KEY,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Health / connectivity
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """Ping the Hindsight API and return its health status."""
        resp = self.session.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Memory CRUD  (placeholder signatures — flesh out in Phase 1)
    # ------------------------------------------------------------------

    def store_memory(self, customer_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a memory payload for a given customer."""
        resp = self.session.post(
            f"{self.base_url}/memories",
            json={"customer_id": customer_id, **payload},
        )
        resp.raise_for_status()
        return resp.json()

    def retrieve_memory(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the stored memory context for a customer."""
        resp = self.session.get(f"{self.base_url}/memories/{customer_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def search_memories(self, query: str, top_k: int = 5) -> list:
        """Semantic search across all stored memories."""
        resp = self.session.post(
            f"{self.base_url}/memories/search",
            json={"query": query, "top_k": top_k},
        )
        resp.raise_for_status()
        return resp.json()
