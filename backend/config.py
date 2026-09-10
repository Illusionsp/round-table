"""
Configuration for Roundtable.

Cost note: the models below default to OpenRouter's *free* tier
(model ids ending in ":free"). Free-tier availability and identifiers
change over time and carry rate limits, so check
https://openrouter.ai/models?max_price=0 before relying on this in
production. Swap in paid models here if you want higher quality/limits.
"""
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Council members that each independently answer, then peer-review each
# other. Keep this list short (3-5) to control cost/latency even on
# free models, since every member is queried in Stage 1 AND Stage 2.
COUNCIL_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-2-9b-it:free",
    "qwen/qwen-2.5-7b-instruct:free",
]

# Model that synthesizes the final answer from all responses + rankings.
# Left on the free tier by default; bump to a stronger paid model
# (e.g. "google/gemini-flash-1.5" or "anthropic/claude-3.5-haiku")
# if the free chairman's synthesis quality isn't good enough.
CHAIRMAN_MODEL = "google/gemma-2-9b-it:free"

# Per-request timeout for OpenRouter calls, in seconds.
REQUEST_TIMEOUT = 60

# CORS origins allowed to hit the API (Vite dev server + CRA default).
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "conversations")
