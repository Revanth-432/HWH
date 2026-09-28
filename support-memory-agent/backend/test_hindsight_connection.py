"""
test_hindsight_connection.py
----------------------------
Quick smoke-test to verify connectivity to the Hindsight memory API.
Run:  python test_hindsight_connection.py
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

HINDSIGHT_API_URL = os.getenv("HINDSIGHT_BASE_URL", os.getenv("HINDSIGHT_API_URL", "http://localhost:8888"))
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "")


def main() -> None:
    print(f"🔗  Testing connection to Hindsight API at: {HINDSIGHT_API_URL}")
    print("-" * 60)

    headers = {
        "Authorization": f"Bearer {HINDSIGHT_API_KEY}",
        "Content-Type": "application/json",
    }

    # --- 1. Health check ---
    try:
        resp = requests.get(f"{HINDSIGHT_API_URL}/health", headers=headers, timeout=10)
        print(f"✅  Health endpoint responded with status {resp.status_code}")
        print(f"    Body: {resp.text[:500]}")
    except requests.ConnectionError:
        print("❌  Connection refused — is the Hindsight server running?")
        sys.exit(1)
    except Exception as exc:
        print(f"❌  Unexpected error: {exc}")
        sys.exit(1)

    # --- 2. Attempt a basic API call (list memories or similar) ---
    try:
        resp = requests.get(f"{HINDSIGHT_API_URL}/memories", headers=headers, timeout=10)
        print(f"\n📦  GET /memories → status {resp.status_code}")
        print(f"    Body: {resp.text[:500]}")
    except Exception as exc:
        print(f"⚠️   Could not list memories: {exc}")

    print("\n" + "=" * 60)
    print("🎉  Hindsight smoke-test complete!")


if __name__ == "__main__":
    main()
