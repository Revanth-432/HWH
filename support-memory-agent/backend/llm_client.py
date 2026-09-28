"""
llm_client.py
-------------
Wrapper around the Groq SDK for LLM-powered support replies,
summarisation, sentiment analysis, and escalation-decision logic.
"""

from __future__ import annotations

import os
import time
import traceback
from typing import Optional

from dotenv import load_dotenv
from groq import Groq, APIConnectionError, RateLimitError, APIStatusError

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
DEFAULT_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")


class LLMClient:
    """High-level interface to the Groq-hosted LLM."""

    def __init__(
        self,
        api_key: str = GROQ_API_KEY,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.client = Groq(api_key=api_key)
        self.model = model

    # ------------------------------------------------------------------
    # Core: get_reply
    # ------------------------------------------------------------------

    def get_reply(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.4,
        max_tokens: int = 1024,
        retries: int = 3,
    ) -> str:
        """Send a chat completion and return the assistant's text.

        Includes robust retry logic for rate-limit (429) and transient
        connection errors.  Raises after *retries* consecutive failures.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content

            except RateLimitError as exc:
                last_error = exc
                wait = min(2 ** attempt, 30)
                print(
                    f"[LLMClient] Rate-limited (attempt {attempt}/{retries}). "
                    f"Waiting {wait}s …"
                )
                time.sleep(wait)

            except APIConnectionError as exc:
                last_error = exc
                wait = min(2 ** attempt, 30)
                print(
                    f"[LLMClient] Connection error (attempt {attempt}/{retries}): {exc}. "
                    f"Waiting {wait}s …"
                )
                time.sleep(wait)

            except APIStatusError as exc:
                last_error = exc
                print(
                    f"[LLMClient] API error {exc.status_code} (attempt {attempt}/{retries}): "
                    f"{exc.message}"
                )
                if exc.status_code >= 500:
                    time.sleep(min(2 ** attempt, 30))
                else:
                    # 4xx (except 429 handled above) → don't retry
                    raise

            except Exception as exc:
                last_error = exc
                print(f"[LLMClient] Unexpected error: {traceback.format_exc()}")
                raise

        raise RuntimeError(
            f"LLM request failed after {retries} attempts. Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Domain helpers (used by the existing app.py routes)
    # ------------------------------------------------------------------

    def chat(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 1024,
    ) -> str:
        """Legacy single-turn helper kept for backward compatibility."""
        return self.get_reply(
            system_prompt=system_prompt or "You are a helpful assistant.",
            user_message=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def summarise_interactions(self, interactions_json: str) -> str:
        """Produce a concise summary of a customer's interaction history."""
        return self.get_reply(
            system_prompt=(
                "You are a helpful customer-support analyst. "
                "Be concise but capture every important detail."
            ),
            user_message=(
                "Summarise the following customer-support interactions into a "
                "brief paragraph. Focus on unresolved issues, attempted fixes, "
                "and customer sentiment.\n\n" + interactions_json
            ),
        )

    def assess_escalation(self, context_summary: str) -> str:
        """Decide whether a ticket should be escalated, and explain why."""
        return self.get_reply(
            system_prompt="You are a support-operations manager.",
            user_message=(
                "Based on the following customer context, should this ticket "
                "be escalated to a senior agent? Answer YES or NO and give a "
                "one-sentence justification.\n\n" + context_summary
            ),
        )
