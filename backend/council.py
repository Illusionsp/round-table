"""
Core 3-stage deliberation logic for Roundtable.

Stage 1: every council model independently answers the user's question.
Stage 2: responses are anonymized ("Response A/B/C...") and each model
         ranks all responses (including its own, unknowingly) so no
         model can play favorites with itself or a well-known peer.
Stage 3: the chairman model synthesizes a final answer using every
         Stage 1 response plus every Stage 2 ranking/critique.
"""
import re
import string
import logging
from typing import List, Dict, Any, Tuple, Optional

from .config import COUNCIL_MODELS, CHAIRMAN_MODEL
from .openrouter import query_models_parallel, query_model

logger = logging.getLogger("roundtable.council")

LABELS = list(string.ascii_uppercase)  # "Response A", "Response B", ...


async def stage1_collect_responses(question: str) -> List[Dict[str, Any]]:
    """
    Query every council model in parallel with the raw user question.
    Returns a list of {"model": str, "content": str|None} — content is
    None for any model that failed, so the caller can filter or flag it.
    """
    messages = [{"role": "user", "content": question}]
    results = await query_models_parallel(COUNCIL_MODELS, messages)

    responses = []
    for model in COUNCIL_MODELS:
        result = results.get(model)
        responses.append({
            "model": model,
            "content": result["content"] if result else None,
        })
    return responses


def parse_ranking_from_text(text: str, valid_labels: List[str]) -> List[str]:
    """
    Extract an ordered list of "Response X" labels from a model's raw
    ranking text. Primary path looks for a "FINAL RANKING:" section with
    a numbered list; fallback scans the whole text for "Response X"
    occurrences in order, deduplicated, in case a model ignores the
    requested format.
    """
    valid_set = set(valid_labels)

    # Primary: look for the FINAL RANKING section.
    match = re.search(r"FINAL RANKING:?\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    section = match.group(1) if match else text

    # Numbered list lines like "1. Response C" or "1) Response C". Require
    # a leading number so we don't mistake prose mentions for list items;
    # use finditer (not search) per line in case a line somehow contains
    # more than one label.
    ordered = []
    for line in section.splitlines():
        if not re.match(r"^\s*\d+[\.\)]", line):
            continue
        for line_match in re.finditer(r"Response\s+([A-Z])", line, re.IGNORECASE):
            label = f"Response {line_match.group(1).upper()}"
            if label.split()[-1] in valid_set and label not in ordered:
                ordered.append(label)

    if ordered:
        return ordered

    # Fallback: scan raw text for any "Response X" mentions in order.
    fallback = []
    for m in re.finditer(r"Response\s+([A-Z])", text, re.IGNORECASE):
        label = f"Response {m.group(1).upper()}"
        if label.split()[-1] in valid_set and label not in fallback:
            fallback.append(label)
    return fallback


def _build_stage2_prompt(question: str, label_to_content: Dict[str, str]) -> str:
    labels = list(label_to_content.keys())
    blocks = "\n\n".join(f"{label}:\n{content}" for label, content in label_to_content.items())
    return f"""You are evaluating multiple AI responses to the same question. Be objective and critical.

QUESTION:
{question}

RESPONSES TO EVALUATE:
{blocks}

Instructions:
1. Evaluate each response individually first — note strengths, weaknesses, accuracy, and depth.
2. Then provide a final ranking from best to worst.
3. End your evaluation with a section that starts exactly with "FINAL RANKING:" followed by a numbered list, one response label per line, e.g.:
FINAL RANKING:
1. {labels[0]}
2. {labels[1] if len(labels) > 1 else labels[0]}
...
Do not add any text after the final ranking section."""


async def stage2_collect_rankings(
    question: str,
    stage1_responses: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Anonymize successful Stage 1 responses, ask every council model to
    rank them, and return (rankings, label_to_model).

    rankings: list of {"model": evaluator_model, "raw_text": str|None,
                        "parsed_ranking": List[str]}
    label_to_model: {"Response A": "openai/gpt-5.1", ...} for de-anon.
    """
    valid = [r for r in stage1_responses if r["content"]]
    if len(valid) < 2:
        # Not enough responses to meaningfully rank against each other.
        return [], {}

    labels = LABELS[: len(valid)]
    label_to_model = {f"Response {label}": r["model"] for label, r in zip(labels, valid)}
    label_to_content = {f"Response {label}": r["content"] for label, r in zip(labels, valid)}
    valid_labels = labels

    prompt = _build_stage2_prompt(question, label_to_content)
    messages = [{"role": "user", "content": prompt}]

    results = await query_models_parallel(COUNCIL_MODELS, messages)

    rankings = []
    for model in COUNCIL_MODELS:
        result = results.get(model)
        raw_text = result["content"] if result else None
        parsed = parse_ranking_from_text(raw_text, valid_labels) if raw_text else []
        rankings.append({
            "model": model,
            "raw_text": raw_text,
            "parsed_ranking": parsed,
        })

    return rankings, label_to_model


def calculate_aggregate_rankings(
    rankings: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Average each response's rank position (0-indexed position + 1)
    across every evaluator that successfully produced a parseable
    ranking. Returns a list sorted best-to-worst:
    [{"model": str, "label": str, "avg_position": float, "vote_count": int}, ...]
    """
    positions: Dict[str, List[int]] = {label: [] for label in label_to_model}

    for ranking in rankings:
        for position, label in enumerate(ranking["parsed_ranking"], start=1):
            if label in positions:
                positions[label].append(position)

    aggregate = []
    for label, model in label_to_model.items():
        votes = positions[label]
        avg_position = sum(votes) / len(votes) if votes else None
        aggregate.append({
            "model": model,
            "label": label,
            "avg_position": avg_position,
            "vote_count": len(votes),
        })

    # Responses with no votes (all evaluators failed to rank them) sort last.
    aggregate.sort(key=lambda x: (x["avg_position"] is None, x["avg_position"] or 0))
    return aggregate


def _build_stage3_prompt(
    question: str,
    stage1_responses: List[Dict[str, Any]],
    rankings: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
) -> str:
    responses_block = "\n\n".join(
        f"[{r['model']}]:\n{r['content']}"
        for r in stage1_responses if r["content"]
    )
    if rankings:
        model_to_label = {v: k for k, v in label_to_model.items()}
        evals_block = "\n\n".join(
            f"[{r['model']} evaluated as]:\n{r['raw_text']}"
            for r in rankings if r["raw_text"]
        )
    else:
        evals_block = "(no peer rankings available)"

    return f"""You are the chairman of an AI council. Multiple AI models independently answered the question below, then peer-reviewed and ranked each other's answers anonymously.

QUESTION:
{question}

INDIVIDUAL RESPONSES:
{responses_block}

PEER EVALUATIONS AND RANKINGS:
{evals_block}

Using the strongest ideas, most accurate information, and best reasoning from across all of the above, write a single, well-organized final answer to the original question. Do not mention the council process itself, model names, or the rankings — just answer the question as well as possible."""


async def stage3_synthesize_final(
    question: str,
    stage1_responses: List[Dict[str, Any]],
    rankings: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
) -> Optional[str]:
    """Chairman synthesizes a final answer from all prior stages."""
    prompt = _build_stage3_prompt(question, stage1_responses, rankings, label_to_model)
    result = await query_model(CHAIRMAN_MODEL, [{"role": "user", "content": prompt}])
    return result["content"] if result else None
