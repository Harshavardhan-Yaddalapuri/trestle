"""Semantic relevance scoring via Ollama LLM.

No embedding model needed — uses the chat model to score each candidate
against the query on a 0-1 scale. Batched to minimize round-trips.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.llm_client import get_llm

_SEMANTIC_SCORE_PROMPT = """You are a relevance scorer for a startup resource search engine.
Given a founder's query and a list of candidate resources, score each resource
on a 0.0-1.0 scale for how well it matches the query.

Scoring criteria:
- 0.9-1.0: Perfect match — the resource is exactly what the founder asked for
- 0.7-0.89: Strong match — highly relevant but maybe different stage/scope
- 0.5-0.69: Partial match — adjacent or tangentially useful
- 0.3-0.49: Weak match — barely related
- 0.0-0.29: Not relevant

Return ONLY a JSON array of floats, one score per resource, in the same order.
Example: [0.92, 0.65, 0.45, 0.88, 0.30]

Founder query: {query}

Candidates:
{candidates}

Scores:"""


async def score_candidates(
    query: str, candidates: List[Dict[str, Any]], batch_size: int = 8
) -> List[float]:
    """Score a list of resource candidates against the query using LLM.

    Returns a list of floats (0-1) parallel to the input candidates list.
    """
    if not candidates:
        return []

    llm = get_llm()

    # Format candidates concisely for the prompt
    def _format_candidate(i: int, c: Dict[str, Any]) -> str:
        name = c.get("name", "Unknown")
        rtype = c.get("type", "other")
        desc = (c.get("description") or "")[:200]
        loc = ", ".join(c.get("location", [])) if c.get("location") else "N/A"
        stage = ", ".join(c.get("stage", [])) if c.get("stage") else "N/A"
        deadline = str(c.get("deadline", "None"))
        return (
            f"[{i}] {name} | type={rtype} | location={loc} | "
            f"stage={stage} | deadline={deadline}\n    {desc}"
        )

    # Batch if large
    all_scores: List[float] = []
    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start : batch_start + batch_size]
        lines = [_format_candidate(batch_start + j, c) for j, c in enumerate(batch)]
        prompt = _SEMANTIC_SCORE_PROMPT.format(
            query=query, candidates="\n\n".join(lines)
        )

        raw: List[float] = []
        try:
            text = await llm.generate(prompt, max_tokens=256, temperature=0.0)
            # Extract JSON array from response
            text = text.strip()
            if "[" in text and "]" in text:
                text = text[text.index("[") : text.rindex("]") + 1]
                from json import loads

                raw = loads(text)
        except Exception:
            # Fallback: neutral scores
            raw = [0.5] * len(batch)

        # Validate and clamp
        scores: List[float] = []
        for i, s in enumerate(raw):
            try:
                score = float(s)
                scores.append(max(0.0, min(1.0, score)))
            except (ValueError, TypeError):
                scores.append(0.5)  # neutral fallback
        all_scores.extend(scores)

    return all_scores
