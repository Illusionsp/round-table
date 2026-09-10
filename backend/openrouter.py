"""
Thin async client for OpenRouter's chat-completions endpoint.

Design goal: never let one model's failure take down the whole request.
query_model() returns None on any error; callers filter Nones out.
"""
import logging
from typing import Optional, List, Dict, Any

import httpx

from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, REQUEST_TIMEOUT

logger = logging.getLogger("roundtable.openrouter")


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
) -> Optional[Dict[str, Any]]:
    """
    Query a single model. Returns {"content": str, "reasoning_details": Any|None}
    on success, or None on failure (logged, never raised to the caller).
    """
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is not set")
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # OpenRouter uses these for its free-tier attribution/leaderboards.
        "HTTP-Referer": "https://github.com/roundtable",
        "X-Title": "Roundtable",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
        if resp.status_code != 200:
            logger.warning("Model %s returned HTTP %s: %s", model, resp.status_code, resp.text[:500])
            return None

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content")
        if not content:
            logger.warning("Model %s returned empty content", model)
            return None

        return {
            "content": content,
            "reasoning_details": message.get("reasoning") or message.get("reasoning_details"),
        }
    except httpx.TimeoutException:
        logger.warning("Model %s timed out after %ss", model, REQUEST_TIMEOUT)
        return None
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see module docstring
        logger.warning("Model %s failed: %s", model, exc)
        return None


import asyncio


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query many models concurrently. Returns {model_id: result_or_None},
    preserving the input order of `models`.
    """
    results = await asyncio.gather(
        *(query_model(m, messages, temperature) for m in models)
    )
    return dict(zip(models, results))
