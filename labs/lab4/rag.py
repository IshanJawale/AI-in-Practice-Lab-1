#!/usr/bin/env python3
"""Lab 4 — your RAG pipeline.

Write this yourself. `aip/rag.py` is the reference implementation; look at it
after Part A, not before. Labs 5-7 build on whichever of the two you prefer,
but you must be able to explain every line of the one you use.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aip.guards import UNTRUSTED_SYSTEM_CLAUSE, delimit_untrusted  # noqa: E402
from aip.llm import chat  # noqa: E402
from aip.retrieval import Hit, Retriever, format_context  # noqa: E402

# The exact string the system must emit when it cannot answer. Exact, because
# downstream code detects refusal by matching it -- a paraphrase is a bug.
REFUSAL = "I don't have enough information in the provided sources to answer that."

# TODO A: write this before you read aip/rag.py::ANSWER_SYSTEM.
ANSWER_SYSTEM = f"""\
You answer questions using ONLY the numbered sources provided.

Rules, in priority order:
1. If the sources do not contain sufficient information to answer the question,
   reply with exactly this string and nothing else:
   "I don't have enough information in the provided sources to answer that."
   Only use this refusal when the sources genuinely lack the required information.
   If the sources contain partial information, answer what IS supported with
   citations and omit what is not — do not refuse the whole question.
   Do not guess, and do not fall back on general knowledge.
2. Every factual sentence must end with a citation of the source(s) that
   support it, in the form [1] or [2][5].
3. Never cite a number that was not given to you.
4. If sources disagree, say so and cite both.
5. Be concise. Two or three sentences unless the question needs more.
6. The answer must not contain any content outside the supplied sources.

{UNTRUSTED_SYSTEM_CLAUSE}
"""



@dataclass
class Answer:
    question: str
    text: str
    hits: list[Hit] = field(default_factory=list)
    refused: bool = False
    citations_valid: bool = False
    invalid_citations: list[int] = field(default_factory=list)
    n_citations: int = 0
    truncated: bool = False


def validate_answer(text: str, n_sources: int, finish_reason: str | None = None) -> dict:
    """Validate an answer according to Lab 4 criteria.

    Returns a dict with keys:
        valid: bool – overall verdict (must be True for non‑refusal answers)
        refused: bool – True if the answer is the exact REFUSAL string
        invalid_citations: list[int] – citation indices that are out of range
        n_citations: int – total number of citations found
        truncated: bool – True if finish_reason indicates truncation ("length")
        reason: str – optional human‑readable explanation
    """
    # Detect refusal by exact match (ignore surrounding whitespace)
    is_refusal = text.strip().startswith(REFUSAL)
    # Find citations like [1] or [2][5]
    citations = [int(m) for m in re.findall(r"\[(\d+)\]", text)]
    invalid = [c for c in citations if c < 1 or c > n_sources]
    truncated = finish_reason == "length"
    # Non‑refusal answers must have at least one citation and be non‑empty
    has_content = bool(text and text.strip())
    valid = True
    reason_parts = []
    if is_refusal:
        # When refusing, we do not require citations or content
        valid = True
    else:
        if not has_content:
            valid = False
            reason_parts.append("empty answer")
        if not citations:
            valid = False
            reason_parts.append("no citations")
        if invalid:
            valid = False
            reason_parts.append(f"invalid citations {invalid}")
        if truncated:
            valid = False
            reason_parts.append("truncated answer")
    return {
        "valid": valid,
        "refused": is_refusal,
        "invalid_citations": invalid,
        "n_citations": len(citations),
        "truncated": truncated,
        "reason": ", ".join(reason_parts),
    }



def answer_question(question: str, retriever: Retriever, *, k: int = 12,
                     final_k: int = 5, reranker=None, tier: str = "MAIN") -> Answer:
    """Run the RAG pipeline: retrieve, optionally rerank, generate, validate.

    If validation fails (and the answer is not already a refusal), we fall back
    to an exact refusal string. This guarantees we never return an answer with
    invalid citations while not refusing.
    """
    # Retrieve hits
    hits = retriever.search(question, k=k)
    # Apply reranker if provided
    if reranker is not None:
        final_hits = reranker.rerank(question, hits, k=final_k)
    else:
        final_hits = hits[:final_k]

    # Generate answer using the structured prompt
    context = delimit_untrusted(format_context(final_hits, max_chars=8000))
    prompt = f"{context}\n\nQuestion: {question}\n\nAnswer with citations:"
    answer_text = chat(prompt, system=ANSWER_SYSTEM, tier=tier,
                      temperature=0.0, max_tokens=600).strip()

    # Validate answer
    validation = validate_answer(answer_text, n_sources=len(final_hits), finish_reason=None)

    # If validation fails and not a refusal, fallback to refusal
    if not validation["valid"] and not validation["refused"]:
        answer_text = REFUSAL
        validation = validate_answer(answer_text, n_sources=0, finish_reason=None)
        final_hits = []

    return Answer(
        question=question,
        text=answer_text,
        hits=list(final_hits),
        refused=validation["refused"],
        citations_valid=validation["valid"],
        invalid_citations=validation["invalid_citations"],
        n_citations=validation["n_citations"],
        truncated=validation["truncated"],
    )


def answer_with_gold_context(question: str, gold_docs: list[str], *,
                             tier: str = "MAIN") -> Answer:
    """Generate an answer using the gold (reference) documents as context.

    The gold documents are provided as raw strings. We treat each as a separate
    source, number them, and pass them to the same generation step as in
    ``answer_question``.
    """
    # Create fake hits for the gold documents – each document becomes one source
    from aip.chunking import Chunk
    hits: list[Hit] = []
    for i, doc in enumerate(gold_docs, start=1):
        # Create a chunk for the whole gold document (no heading prefix needed)
        chunk = Chunk(text=doc, doc_id=f"gold_{i}", chunk_id=f"gold_{i}::g0")
        hits.append(Hit(chunk, score=0.0, source="gold", rank=i - 1))

    # Build context and generate answer
    context = delimit_untrusted(format_context(hits, max_chars=8000))
    prompt = f"{context}\n\nQuestion: {question}\n\nAnswer with citations:"
    answer_text = chat(prompt, system=ANSWER_SYSTEM, tier=tier,
                      temperature=0.0, max_tokens=600).strip()

    # Validate answer (n_sources is len(gold_docs))
    validation = validate_answer(answer_text, n_sources=len(gold_docs), finish_reason=None)

    # If validation fails and not a refusal, fall back to REFUSAL
    if not validation["valid"] and not validation["refused"]:
        answer_text = REFUSAL
        validation = validate_answer(answer_text, n_sources=0, finish_reason=None)
        hits = []

    return Answer(
        question=question,
        text=answer_text,
        hits=hits,
        refused=validation["refused"],
        citations_valid=validation["valid"],
        invalid_citations=validation["invalid_citations"],
        n_citations=validation["n_citations"],
        truncated=validation["truncated"],
    )
