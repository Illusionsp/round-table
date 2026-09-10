"""
Minimal JSON-file conversation storage — no database needed, which
keeps this at zero infra cost. Each conversation is one JSON file:
{id, created_at, messages: [{role, content?, stage1?, stage2?, stage3?}]}

Note: per-response metadata (label_to_model, aggregate_rankings) is
intentionally NOT persisted here — it's ephemeral, returned only in the
live API response, since anonymization mappings are only meaningful for
the request that produced them.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .config import DATA_DIR

os.makedirs(DATA_DIR, exist_ok=True)


def _path(conversation_id: str) -> str:
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


def create_conversation() -> Dict[str, Any]:
    conversation = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "messages": [],
    }
    _save(conversation)
    return conversation


def _save(conversation: Dict[str, Any]) -> None:
    with open(_path(conversation["id"]), "w", encoding="utf-8") as f:
        json.dump(conversation, f, indent=2)


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    path = _path(conversation_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_conversations() -> List[Dict[str, Any]]:
    """Returns lightweight summaries (id, created_at, first user message)."""
    summaries = []
    if not os.path.isdir(DATA_DIR):
        return summaries
    for filename in sorted(os.listdir(DATA_DIR), reverse=True):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
            conv = json.load(f)
        first_user_msg = next(
            (m["content"] for m in conv["messages"] if m["role"] == "user"), ""
        )
        summaries.append({
            "id": conv["id"],
            "created_at": conv["created_at"],
            "preview": (first_user_msg or "")[:80],
        })
    return summaries


def append_message(conversation_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    conversation["messages"].append(message)
    _save(conversation)
    return conversation


def delete_conversation(conversation_id: str) -> bool:
    path = _path(conversation_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
