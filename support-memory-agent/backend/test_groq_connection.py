"""
test_groq_connection.py
-----------------------
Quick smoke-test to verify the Groq API key and model access.
Run:  python test_groq_connection.py
"""

import os
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Models to try, in order of preference
MODELS_TO_TRY = [
    "qwen/qwen3-32b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
]


def main() -> None:
    if not GROQ_API_KEY:
        print("❌  GROQ_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)

    client = Groq(api_key=GROQ_API_KEY)
    print("🔗  Groq client initialised successfully.")
    print("-" * 60)

    for model in MODELS_TO_TRY:
        print(f"\n🧪  Trying model: {model}")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Say 'Hello from Groq!' and nothing else. "
                            "This is a connectivity test."
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=64,
            )
            reply = response.choices[0].message.content
            print(f"✅  Model responded: {reply}")
            print(f"    Usage: {response.usage}")
            print("\n" + "=" * 60)
            print("🎉  Groq smoke-test passed!")
            return
        except Exception as exc:
            print(f"⚠️   Model {model} failed: {exc}")

    print("\n❌  All models failed. Check your API key and account limits.")
    sys.exit(1)


if __name__ == "__main__":
    main()
