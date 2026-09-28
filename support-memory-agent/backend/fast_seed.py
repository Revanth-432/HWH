"""
fast_seed.py — Reload seed data with shorter pauses (2s instead of 28s).
The Hindsight API uses its own LLM key for embedding, so we only need
to stay under Hindsight's rate limits, not Groq's chat limits.
"""
import json, sys, time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from memory_store import MemoryStore

SEED = Path(__file__).resolve().parent.parent / "data" / "seed_customers.json"
store = MemoryStore()

with open(SEED, "r", encoding="utf-8") as f:
    customers = json.load(f)

total = sum(len(c.get("interactions", [])) for c in customers)
print(f"Loading {total} interactions for {len(customers)} customers ...\n")

loaded = 0
for customer in customers:
    name, email = customer["name"], customer["email"]
    interactions = customer.get("interactions", [])
    print(f"  > {name} ({email}) -- {len(interactions)} interactions")

    for idx, ix in enumerate(interactions, 1):
        ts = datetime.fromisoformat(ix["timestamp"].replace("Z", "+00:00"))
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                store.remember_interaction(
                    customer_id=email,
                    channel=ix.get("channel", "chat"),
                    message=ix.get("message", ""),
                    issue_summary=ix.get("message", "")[:120],
                    attempted_fix=ix.get("attempted_fix", "No fix attempted."),
                    resolution_status=ix.get("resolution_status", "open"),
                    sentiment=ix.get("sentiment", "neutral"),
                    contact_count=idx,
                    timestamp=ts,
                    tags=ix.get("tags", []) + [ix.get("channel","chat"), ix.get("resolution_status","open"), ix.get("sentiment","neutral")],
                )
                loaded += 1
                print(f"    [OK] {ix.get('interaction_id', idx)}")
                break
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate limit" in err_msg.lower() or "500" in err_msg:
                    print(f"    [RATE LIMIT] attempt {attempt+1}/{max_retries}, sleeping 25s... (Error: {err_msg})")
                    time.sleep(25)
                else:
                    print(f"    [FAIL] {ix.get('interaction_id', idx)}: {e}")
                    break
        time.sleep(5)
    print()

print(f"Done — {loaded}/{total} interactions loaded.\n")
