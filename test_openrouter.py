"""
Quick standalone connectivity check for OpenRouter — run this before
adding a new model to COUNCIL_MODELS in backend/config.py, to confirm
the model id is valid and reachable on your key/tier.

Usage:
    python test_openrouter.py "meta-llama/llama-3.1-8b-instruct:free"
"""
import asyncio
import sys

from backend.openrouter import query_model


async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "meta-llama/llama-3.1-8b-instruct:free"
    print(f"Testing model: {model}")
    result = await query_model(model, [{"role": "user", "content": "Say 'ok' and nothing else."}])
    if result is None:
        print("FAILED — see logged warning above for the reason.")
        sys.exit(1)
    print("SUCCESS")
    print("Content:", result["content"])
    if result.get("reasoning_details"):
        print("Reasoning details present:", bool(result["reasoning_details"]))


if __name__ == "__main__":
    asyncio.run(main())
