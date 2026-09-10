"""
Roundtable backend — FastAPI app.

Run from the project root with:
    python -m backend.main
(relative imports below require this; running `python backend/main.py`
directly will break the `from .config import ...` style imports.)
"""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import storage
from .config import ALLOWED_ORIGINS
from .council import (
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("roundtable.main")

app = FastAPI(title="Roundtable API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageRequest(BaseModel):
    content: str


@app.get("/api/conversations")
def list_conversations():
    return storage.list_conversations()


@app.post("/api/conversations")
def create_conversation():
    return storage.create_conversation()


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    if not storage.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: MessageRequest):
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    question = request.content
    storage.append_message(conversation_id, {"role": "user", "content": question})

    stage1 = await stage1_collect_responses(question)
    if not any(r["content"] for r in stage1):
        raise HTTPException(
            status_code=502,
            detail="All council models failed to respond. Check OPENROUTER_API_KEY and model availability.",
        )

    rankings, label_to_model = await stage2_collect_rankings(question, stage1)
    aggregate_rankings = (
        calculate_aggregate_rankings(rankings, label_to_model) if rankings else []
    )
    stage3 = await stage3_synthesize_final(question, stage1, rankings, label_to_model)

    assistant_message = {
        "role": "assistant",
        "stage1": stage1,
        "stage2": rankings,
        "stage3": stage3,
    }
    conversation = storage.append_message(conversation_id, assistant_message)

    # Metadata is ephemeral: returned here for the frontend to render,
    # but deliberately not written into the persisted conversation JSON.
    return {
        "conversation": conversation,
        "metadata": {
            "label_to_model": label_to_model,
            "aggregate_rankings": aggregate_rankings,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)
