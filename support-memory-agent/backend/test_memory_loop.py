"""
test_memory_loop.py
-------------------
CLI test script that validates the core memory loop.

1. Sends a message from "Priya Sharma" (4 unresolved contacts) WITH memory
   → should trigger the escalation rule.
2. Sends the exact same message WITHOUT memory
   → should produce a generic first-contact response.

Usage:
    python test_memory_loop.py
"""

from __future__ import annotations

import sys
import textwrap

from dotenv import load_dotenv

load_dotenv()

from agent import handle_customer_message

# ── Test parameters ──────────────────────────────────────────────────────────

CUSTOMER_ID = "priya.sharma@example.com"
CHANNEL = "chat"
TEST_MESSAGE = (
    "Hi, this is Priya again. I've been contacting you for over a week now "
    "about the duplicate billing charge on my Pro plan. I was promised a "
    "refund 9 days ago and it still hasn't arrived. I've already filed a "
    "dispute with my bank. Please help me resolve this once and for all."
)

DIVIDER = "=" * 70


def print_section(title: str, body: str) -> None:
    """Pretty-print a labelled section."""
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)
    wrapped = textwrap.fill(body, width=68, initial_indent="  ", subsequent_indent="  ")
    print(wrapped)
    print()


def main() -> None:
    print("\n" + "#" * 70)
    print("  MEMORY LOOP TEST -- Priya Sharma (escalation scenario)")
    print("#" * 70)

    # ── Test 1: Memory ON (should escalate) ──────────────────────────────
    print("\n[...] Test 1 -- Memory ON ... calling handle_customer_message()")
    result_on = handle_customer_message(
        customer_id=CUSTOMER_ID,
        channel=CHANNEL,
        message=TEST_MESSAGE,
        memory_off=False,
    )

    print_section(
        "TEST 1 — MEMORY ON (expect ESCALATION)",
        result_on["reply"],
    )
    print(f"  Memory results recalled : {result_on['memory_results_count']}")
    print(f"  Interaction retained    : {result_on['retain_result'] is not None}")
    print()

    # ── Test 2: Memory OFF (should be generic) ───────────────────────────
    print("[...] Test 2 -- Memory OFF ... calling handle_customer_message()")
    result_off = handle_customer_message(
        customer_id=CUSTOMER_ID,
        channel=CHANNEL,
        message=TEST_MESSAGE,
        memory_off=True,
    )

    print_section(
        "TEST 2 — MEMORY OFF (expect GENERIC response)",
        result_off["reply"],
    )
    print(f"  Memory results recalled : {result_off['memory_results_count']}")
    print(f"  Interaction retained    : {result_off['retain_result'] is not None}")

    # ── Verdict ──────────────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    reply_on_lower = result_on["reply"].lower()
    escalated = any(
        kw in reply_on_lower
        for kw in ["escalat", "senior agent", "supervisor", "manager"]
    )
    esc_label = "YES" if escalated else "NO"
    mem_on_label = "YES" if result_on['memory_used'] else "NO"
    mem_off_label = "YES" if not result_off['memory_used'] else "NO"
    print(f"  ESCALATION detected in Test 1: {esc_label}")
    print(f"  Memory was used in Test 1    : {mem_on_label}")
    print(f"  Memory was OFF  in Test 2    : {mem_off_label}")
    print(DIVIDER + "\n")

    if not escalated:
        print("WARNING: The LLM did NOT produce an escalation message. This may mean")
        print("   the seed data was not loaded. Run `python load_seed_data.py` first.\n")


if __name__ == "__main__":
    main()
