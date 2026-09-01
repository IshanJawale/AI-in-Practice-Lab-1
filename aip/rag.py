"""A reference RAG pipeline, written as seven named stages.

Lab 4 asks you to build your own from a skeleton. This file exists so that
Labs 5-7 have a working baseline to improve on, and so you have something to
compare your implementation against.

The reason it is structured as seven explicit stages is the reason for the
whole of Lab 5: when a RAG system gives a wrong answer, "RAG is bad" is not a
diagnosis. Exactly one of these stages usually failed, and each has a
different fix:

    1. ingest    the document was never in the corpus            -> data
    2. chunk     the answer was split across two chunks          -> chunking
    3. embed     the query and passage words do not overlap      -> hybrid/HyDE
    4. retrieve  the right chunk existed but ranked 14th         -> k, rerank
    5. rerank    the right chunk was in the pool but discarded   -> reranker
    6. generate  the right chunk was in context and was ignored  -> prompt
    7. present   correct answer, wrong or missing citation       -> output contract

Trace every stage (this file does) and the diagnosis takes a minute instead
of an afternoon.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from aip import tracing
from aip.chunking import Chunk, STRATEGIES
from aip.guards import UNTRUSTED_SYSTEM_CLAUSE, delimit_untrusted, enforce_citations
from aip.llm import chat
from aip.retrieval import Hit, Retriever, format_context

ANSWER_SYSTEM = f"""\
You answer questions using ONLY the numbered sources provided.

Rules, in priority order:
1. If the sources do not contain the answer, reply exactly:
   "I don't have enough information in the provided sources to answer that."
   Do not guess, and do not fall back on general knowledge.
2. Every factual sentence must end with a citation of the source(s) that
   support it, in the form [1] or [2][5].
3. Never cite a number that was not given to you.
4. If sources disagree, say so and cite both.
5. Be concise. Two or three sentences unless the question needs more.

{UNTRUSTED_SYSTEM_CLAUSE}
"""


@dataclass
class RagAnswer:
    question: str
    answer: str
    hits: list[Hit] = field(default_factory=list)
    citations_valid: bool = True
    invalid_citations: list[int] = field(default_factory=list)
    refused: bool = False
    stages: dict[str, Any] = field(default_factory=dict)

    @property
    def cited_doc_ids(self) -> list[str]:
        import re

        idx = sorted({int(m) for m in re.findall(r"\[(\d+)\]", self.answer)})
        return [self.hits[i - 1].doc_id for i in idx if 1 <= i <= len(self.hits)]


REFUSAL = "I don't have enough information in the provided sources to answer that."


class RagPipeline:
    """Compose a retriever, an optional reranker, and a generator.

        pipe = RagPipeline(retriever, reranker=reranker, k=20, final_k=5)
        out  = pipe.answer("What is the claim window for out-patient cover?")
    """

    def __init__(
        self,
        retriever: Retriever,
        *,
        reranker: Any | None = None,
        k: int = 12,
        final_k: int = 5,
        tier: str = "MAIN",
        max_context_chars: int = 8000,
        query_transform: Callable[[str], str] | None = None,
        system: str = ANSWER_SYSTEM,
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.k = k
        self.final_k = final_k
        self.tier = tier
        self.max_context_chars = max_context_chars
        self.query_transform = query_transform
        self.system = system

    # -- stage 3/4 -------------------------------------------------------
    def retrieve(self, question: str) -> list[Hit]:
        q = self.query_transform(question) if self.query_transform else question
        with tracing.trace("rag.retrieve", k=self.k, transformed=q != question) as s:
            hits = self.retriever.search(q, k=self.k)
            s["n_hits"] = len(hits)
            s["top_doc"] = hits[0].doc_id if hits else None
        return hits

    # -- stage 5 ---------------------------------------------------------
    def rerank(self, question: str, hits: Sequence[Hit]) -> list[Hit]:
        if not self.reranker:
            return list(hits)[: self.final_k]
        with tracing.trace("rag.rerank", n_in=len(hits), n_out=self.final_k):
            return self.reranker.rerank(question, hits, k=self.final_k)

    # -- stage 6/7 -------------------------------------------------------
    def generate(self, question: str, hits: Sequence[Hit]) -> str:
        context = delimit_untrusted(
            format_context(hits, max_chars=self.max_context_chars)
        )
        prompt = f"{context}\n\nQuestion: {question}\n\nAnswer with citations:"
        with tracing.trace("rag.generate", n_sources=len(hits), tier=self.tier):
            return chat(prompt, system=self.system, tier=self.tier,
                        temperature=0.0, max_tokens=600).strip()

    def answer(self, question: str) -> RagAnswer:
        with tracing.trace("rag.answer", question=question[:120]):
            hits = self.retrieve(question)
            final = self.rerank(question, hits)
            text = self.generate(question, final)
            ok, invalid = enforce_citations(text, len(final))
            refused = text.strip().startswith(REFUSAL[:40])
            return RagAnswer(
                question=question,
                answer=text,
                hits=list(final),
                citations_valid=ok or refused,
                invalid_citations=invalid,
                refused=refused,
                stages={
                    "retrieved": [h.doc_id for h in hits],
                    "final": [h.doc_id for h in final],
                    "retrieve_k": self.k,
                    "final_k": self.final_k,
                },
            )


# --------------------------------------------------------------------------
# Query transforms (Lab 5)
# --------------------------------------------------------------------------
def hyde(question: str, tier: str = "SMALL") -> str:
    """Hypothetical Document Embeddings.

    Ask the model to *write the passage that would answer the question*, then
    embed that instead of the question. It works because questions and
    passages live in different regions of embedding space: "how long do I have
    to file?" shares almost no vocabulary with "Claims must be submitted
    within 30 days of discharge." A hypothetical answer does.

    Gao et al. (2022), arxiv.org/abs/2212.10496. Costs one extra small-model
    call per query — measure whether it earns it.
    """
    draft = chat(
        f"Write a short factual paragraph that would answer this question, in the "
        f"style of a policy document. Invent plausible specifics; accuracy does not "
        f"matter, only phrasing.\n\nQuestion: {question}",
        tier=tier, max_tokens=180, temperature=0.0,
    )
    return f"{question}\n{draft}"


def multi_query(question: str, n: int = 3, tier: str = "SMALL") -> list[str]:
    """Generate paraphrases; retrieve for each; fuse with RRF.

    Buys recall when users phrase things unpredictably. Costs one small call
    plus n retrievals per query.
    """
    from aip.llm import chat as _chat, extract_json

    out = _chat(
        f"Rewrite this question in {n} different ways that a search engine would "
        f'match differently. Reply as a JSON list of strings.\n\n{question}',
        tier=tier, max_tokens=250, temperature=0.3,
    )
    try:
        variants = [str(v) for v in extract_json(out)][:n]
    except ValueError:
        variants = []
    return [question, *variants]
