"""
load_seed_data.py
-----------------
CLI script that reads ``data/seed_customers.json`` and pre-populates
the local Hindsight database by calling ``remember_interaction()`` for
every historical interaction.

Usage:
    python load_seed_data.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from memory_store import MemoryStore

SEED_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_customers.json"


def load_seed_data(store: MemoryStore | None = None) -> None:
    """Read seed_customers.json and retain every interaction in Hindsight."""
    store = store or MemoryStore()

    if not SEED_DATA_PATH.exists():
        print(f"ERROR: Seed data not found at {SEED_DATA_PATH}")
        sys.exit(1)

    with open(SEED_DATA_PATH, "r", encoding="utf-8") as fh:
        customers = json.load(fh)

    total = sum(len(c.get("interactions", [])) for c in customers)
    print(f"Loading {total} interactions for {len(customers)} customers...\n")

    loaded = 0
    for customer in customers:
        name = customer["name"]
        email = customer["email"]
        interactions = customer.get("interactions", [])

        print(f"  > {name} ({email}) -- {len(interactions)} interactions")

        for idx, interaction in enumerate(interactions, start=1):
            # Parse the timestamp from the seed data.
            ts = datetime.fromisoformat(interaction["timestamp"].replace("Z", "+00:00"))

            # Use tags from the seed data if available.
            tags = interaction.get("tags", [])
            channel = interaction.get("channel", "chat")
            resolution_status = interaction.get("resolution_status", "open")
            sentiment = interaction.get("sentiment", "neutral")

            # Build a summary from the message (first 120 chars).
            message = interaction.get("message", "")
            issue_summary = message[:120]

            attempted_fix = interaction.get("attempted_fix", "No fix attempted.")

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = store.remember_interaction(
                        customer_id=email,
                        channel=channel,
                        message=message,
                        issue_summary=issue_summary,
                        attempted_fix=attempted_fix,
                        resolution_status=resolution_status,
                        sentiment=sentiment,
                        contact_count=idx,
                        timestamp=ts,
                        tags=tags + [channel, resolution_status, sentiment],
                    )
                    loaded += 1
                    print(f"    [OK] Interaction {interaction.get('interaction_id', idx)} retained")
                    break
                except Exception as exc:
                    print(f"    [WARN] Attempt {attempt+1} failed to retain interaction {interaction.get('interaction_id', idx)}: {exc}")
                    if attempt < max_retries - 1:
                        print("    [WAIT] Sleeping 30s before retry to reset rate limits...")
                        time.sleep(30)
                    else:
                        print(f"    [FAIL] Failed permanently to retain interaction {interaction.get('interaction_id', idx)}.")

            # Strict pause to respect 7000/8000 TPM limit (1 request per ~30s)
            time.sleep(28)

        print()

    print(f"Done — {loaded}/{total} interactions loaded into Hindsight.\n")


if __name__ == "__main__":
    load_seed_data()
