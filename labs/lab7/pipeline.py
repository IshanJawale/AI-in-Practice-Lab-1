#!/usr/bin/env python3
"""Lab 7 — the request-path pipeline.

One class, ``AskPipeline``, owns everything that happens between "a question
arrives" and "an answer leaves":

    guard-in -> exact cache -> embed -> semantic cache -> retrieve -> rerank
             -> generate -> validate -> guard-out

It is shared by ``service.py`` (HTTP) and ``gate.py`` (CI), so the number the
gate measures is the number the service actually serves. Each stage opens an
``aip.tracing`` span (``svc.*``), which is what the dashboard and the latency
budget in the report are computed from.

Design notes (the reasoning lives here because the report quotes it):

* Retrieval + prompt are *byte-identical* to ``labs/lab4/rag.py`` (markdown
  chunks @ 400 chars, dense retrieval, k=12, final_k=10 -- the Lab 5 winner).
  That keeps the Lab 4/5 numbers comparable and the response cache shared.
* Lab 6 guards on the request path: PII redaction + heuristic injection
  detector on the way in (Layer 2, the best block-rate-per-false-positive in
  Lab 6), ``delimit_untrusted`` on retrieved text (Layer 1), citation
  enforcement and an exfiltration/prompt-leak output filter on the way out
  (Layer 5). A prompt-injection hit is answered with a refusal, not a 4xx:
  the caller did nothing the HTTP layer can call malformed.
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import re
import sys
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

# The repo's .env sets AIP_CACHE=0 for earlier labs. The service needs the disk
# cache on (it holds the corpus embeddings, so start-up is seconds not minutes,
# and it is what AIP_OFFLINE replays). An explicit shell value still wins.
os.environ.setdefault("AIP_CACHE", "1")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from aip import tracing  # noqa: E402
from aip.chunking import markdown_chunks  # noqa: E402
from aip.config import resolve_model, settings  # noqa: E402
from aip.cost import BudgetExceeded  # noqa: E402
from aip.embed import embed  # noqa: E402
from aip.guards import (  # noqa: E402
    delimit_untrusted,
    detect_injection,
    redact_pii,
)
from aip.llm import chat  # noqa: E402
from aip.retrieval import DenseRetriever, Hit, format_context  # noqa: E402
from labs.lab3.search import load_corpus  # noqa: E402
from labs.lab4.rag import ANSWER_SYSTEM, REFUSAL, validate_answer  # noqa: E402

# --- configuration ----------------------------------------------------------
CHUNK_SIZE = 400          # Lab 3 winner (markdown chunking)
RETRIEVE_K = 12           # first-stage pool, as in Lab 4
FINAL_K = 10              # Lab 5 fix: pass 10 chunks, not 5
EXACT_CACHE_SIZE = 2048
SEMANTIC_CACHE_SIZE = 2048
# Measured, not reasoned: see reports/lab7_semantic_cache.json and the report.
SEMANTIC_THRESHOLD = float(os.getenv("AIP_SEMANTIC_THRESHOLD", "0.93"))
DAILY_BUDGET_USD = float(os.getenv("AIP_SERVICE_BUDGET_USD", "1.00"))

BLOCKED_MESSAGE = ("I can't help with that request. It looks like it contains "
                   "instructions aimed at the assistant rather than a question "
                   "about Aurora's policies.")
_LEAK = re.compile(r"RETRIEVED_DOCUMENT|only the numbered sources|UNTRUSTED", re.I)
_EXFIL = re.compile(r"!\[[^\]]*\]\(https?://|https?://\S+\?\S*=", re.I)
_NORM_WS = re.compile(r"\s+")
# Tokens that change the *answer* while barely moving the embedding. Two
# questions that differ in any of these must never share a cache entry.
_DISCRIMINATORS = re.compile(
    r"\b(bronze|silver|gold|platinum|senior|top-?up|super|maternity|"
    r"critical|motor|travel|group|family|floater|opd|ipd|"
    r"\d+(?:[.,]\d+)?)\b", re.I)


# --- model-outage classification -------------------------------------------
class UpstreamUnavailable(RuntimeError):
    """The model/embedding provider is down, throttled, or unreachable."""

    def __init__(self, message: str, retry_after_s: int = 10):
        super().__init__(message)
        self.retry_after_s = retry_after_s


_OUTAGE_MARKERS = ("ratelimit", "timeout", "overloaded", "apiconnection",
                   "internalserver", "serviceunavailable", "badgateway",
                   "cachemiss", "429", "503", "502", "500", "529")


def is_outage(exc: BaseException) -> bool:
    """True for provider-side failures that a client should retry later."""
    if isinstance(exc, (UpstreamUnavailable, ConnectionError, TimeoutError)):
        return True
    blob = f"{type(exc).__name__} {exc}".lower()
    return any(m in blob for m in _OUTAGE_MARKERS)


def retry_after(exc: BaseException) -> int:
    m = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc), re.I)
    if m:
        return max(1, min(120, int(float(m.group(1))) + 1))
    return getattr(exc, "retry_after_s", 10)


# --- result type -------------------------------------------------------------
@dataclass
class Result:
    question: str
    answer: str
    refused: bool = False
    blocked: bool = False
    valid: bool = True
    citations: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    retrieved_docs: list[str] = field(default_factory=list)   # first-stage order
    hits: list[Hit] = field(default_factory=list)
    invalid_citations: list[int] = field(default_factory=list)
    latency_ms: float = 0.0
    cost_usd: float = 0.0            # what this request was actually billed
    list_cost_usd: float = 0.0       # what it would cost cold (== cost when uncached)
    llm_latency_ms: float = 0.0      # generation time as originally recorded
    cached: bool = False
    cache_layer: str = ""            # "" | "exact" | "semantic"
    stages: dict[str, float] = field(default_factory=dict)
    trace_id: str = ""
    n_llm_calls: int = 0


def normalise(question: str) -> str:
    q = _NORM_WS.sub(" ", question.strip().lower())
    return q.rstrip(" ?.!")


def _discriminators(q: str) -> frozenset[str]:
    return frozenset(m.group(1).lower() for m in _DISCRIMINATORS.finditer(q))


class _Stages:
    """Collects per-stage wall-clock ms while opening a tracing span for each."""

    def __init__(self) -> None:
        self.ms: dict[str, float] = {}

    @contextlib.contextmanager
    def __call__(self, name: str, **attrs: Any) -> Iterator[dict]:
        t0 = time.perf_counter()
        with tracing.trace(f"svc.{name}", **attrs) as span:
            try:
                yield span
            finally:
                self.ms[name] = self.ms.get(name, 0.0) + (time.perf_counter() - t0) * 1000


class AskPipeline:
    """Built once at start-up. Thread-safe for concurrent requests."""

    def __init__(self, *, final_k: int = FINAL_K, retrieve_k: int = RETRIEVE_K,
                 semantic_threshold: float | None = None,
                 entity_guard: bool = True, show_progress: bool = False):
        corpus = load_corpus()
        chunks = [c for doc_id, text in corpus.items()
                  for c in markdown_chunks(text, doc_id, size=CHUNK_SIZE)]
        t0 = time.perf_counter()
        self.retriever = DenseRetriever(chunks, show_progress=show_progress)
        self.build_seconds = time.perf_counter() - t0
        self.n_chunks, self.n_docs = len(chunks), len(corpus)
        self.final_k, self.retrieve_k = final_k, retrieve_k
        self.threshold = SEMANTIC_THRESHOLD if semantic_threshold is None else semantic_threshold
        self.entity_guard = entity_guard
        self._exact: OrderedDict[str, Result] = OrderedDict()
        self._semantic: list[tuple[np.ndarray, str, frozenset, tuple, Result]] = []
        self._lock = threading.Lock()
        self.spent_today_usd = 0.0
        self._day = time.strftime("%Y-%m-%d")
        self.counters = {"exact_hits": 0, "semantic_hits": 0, "misses": 0, "blocked": 0}

    # -- budget -----------------------------------------------------------
    def _charge(self, usd: float) -> None:
        with self._lock:
            today = time.strftime("%Y-%m-%d")
            if today != self._day:
                self._day, self.spent_today_usd = today, 0.0
            self.spent_today_usd += usd

    def _check_budget(self) -> None:
        with self._lock:
            if self.spent_today_usd >= DAILY_BUDGET_USD:
                raise BudgetExceeded(
                    f"service daily budget ${DAILY_BUDGET_USD:.2f} exhausted "
                    f"(spent ${self.spent_today_usd:.4f})")

    # -- cache layers -------------------------------------------------------
    @staticmethod
    def _key(question: str, top_k: int, mode: str) -> str:
        blob = f"{mode}|{top_k}|{normalise(question)}"
        return hashlib.sha256(blob.encode()).hexdigest()

    def _exact_get(self, key: str) -> Result | None:
        with self._lock:
            r = self._exact.get(key)
            if r is not None:
                self._exact.move_to_end(key)
            return r

    def _store(self, key: str, question: str, qvec: np.ndarray | None,
               top_k: int, mode: str, result: Result) -> None:
        if result.blocked or not result.valid:
            return                                  # never cache a bad outcome
        with self._lock:
            self._exact[key] = result
            while len(self._exact) > EXACT_CACHE_SIZE:
                self._exact.popitem(last=False)
            if qvec is not None:
                self._semantic.append((qvec, normalise(question),
                                       _discriminators(question), (top_k, mode), result))
                del self._semantic[:-SEMANTIC_CACHE_SIZE]

    def semantic_lookup(self, question: str, qvec: np.ndarray, top_k: int,
                        mode: str) -> tuple[Result | None, float]:
        """Best cached answer at cosine >= threshold. Returns (result, best_cosine)."""
        with self._lock:
            entries = [e for e in self._semantic if e[3] == (top_k, mode)]
        if not entries:
            return None, 0.0
        mat = np.stack([e[0] for e in entries])
        sims = mat @ qvec
        order = np.argsort(-sims)
        want = _discriminators(question)
        for i in order[:5]:
            if sims[i] < self.threshold:
                break
            if self.entity_guard and entries[i][2] != want:
                continue                            # same words, different plan/number
            return entries[i][4], float(sims[i])
        return None, float(sims[order[0]])

    # -- guards -------------------------------------------------------------
    @staticmethod
    def guard_input(question: str) -> tuple[str, dict[str, int], list[str]]:
        clean, pii = redact_pii(question)
        verdict = detect_injection(clean)
        return clean, pii, verdict.signals if verdict.flagged else []

    @staticmethod
    def guard_output(text: str) -> bool:
        """False if the answer leaks prompt text or carries an exfil-style URL."""
        return not (_LEAK.search(text) or _EXFIL.search(text))

    # -- stages -------------------------------------------------------------
    def _retrieve(self, qvec: np.ndarray, k: int) -> list[Hit]:
        scores = self.retriever.matrix @ qvec
        top = np.argsort(-scores)[:k]
        return [Hit(self.retriever.chunks[i], float(scores[i]), "dense", r)
                for r, i in enumerate(top)]

    def build_prompt(self, question: str, hits: list[Hit]) -> str:
        context = delimit_untrusted(format_context(hits, max_chars=8000))
        return f"{context}\n\nQuestion: {question}\n\nAnswer with citations:"

    def _finish(self, res: Result, text: str, final: list[Hit],
                finish_reason: str | None, stages: _Stages) -> None:
        with stages("validate"):
            v = validate_answer(text, n_sources=len(final), finish_reason=finish_reason)
            if not self.guard_output(text):
                text, v = REFUSAL, validate_answer(REFUSAL, 0)
                tracing.event("guard.output_blocked")
            elif not v["valid"] and not v["refused"]:
                tracing.event("guard.citation_fallback", reason=v["reason"])
                text, v, final = REFUSAL, validate_answer(REFUSAL, 0), []
            cited = sorted({int(m) for m in re.findall(r"\[(\d+)\]", text)})
            res.answer, res.refused, res.valid = text, v["refused"], v["valid"]
            res.invalid_citations = v["invalid_citations"]
            res.hits = list(final)
            res.citations = [
                {"index": i, "doc_id": final[i - 1].doc_id,
                 "excerpt": final[i - 1].text.strip()[:700]}
                for i in cited if 1 <= i <= len(final)]
            res.sources = list(dict.fromkeys(c["doc_id"] for c in res.citations))

    # -- the request ----------------------------------------------------------
    def ask(self, question: str, *, top_k: int | None = None, mode: str = "rag",
            use_cache: bool = True) -> Result:
        t0 = time.perf_counter()
        k_final = top_k or self.final_k
        stages = _Stages()
        with tracing.trace("http.ask", question=question[:120], mode=mode) as root:
            res = Result(question=question, answer="", trace_id=root["span_id"])
            try:
                self._ask(res, question, k_final, mode, use_cache, stages)
            finally:
                res.stages = {k: round(v, 2) for k, v in stages.ms.items()}
                res.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                root.update(cached=res.cached, cache_layer=res.cache_layer,
                            cost_usd=res.cost_usd, refused=res.refused,
                            blocked=res.blocked, latency_ms=res.latency_ms,
                            n_citations=len(res.citations))
        return res

    def _ask(self, res: Result, question: str, k_final: int, mode: str,
             use_cache: bool, stages: _Stages) -> None:
        with stages("guard_in"):
            clean, pii, flags = self.guard_input(question)
            if pii:
                tracing.event("guard.pii_redacted", counts=pii)
        if flags:
            self.counters["blocked"] += 1
            res.answer, res.refused, res.blocked = BLOCKED_MESSAGE, True, True
            tracing.event("guard.blocked_input", signals=flags)
            return

        key = self._key(clean, k_final, mode)
        if use_cache:
            with stages("cache_exact") as span:
                hit = self._exact_get(key)
                span["hit"] = hit is not None
            if hit is not None:
                self.counters["exact_hits"] += 1
                self._copy_cached(res, hit, "exact")
                return

        self._check_budget()
        with stages("embed"):
            qvec = embed(clean, input_type="query")

        if use_cache:
            with stages("cache_semantic") as span:
                hit, sim = self.semantic_lookup(clean, qvec, k_final, mode)
                span.update(hit=hit is not None, best_cosine=round(sim, 4))
            if hit is not None:
                self.counters["semantic_hits"] += 1
                self._copy_cached(res, hit, "semantic")
                return
        self.counters["misses"] += 1

        with stages("retrieve", k=self.retrieve_k) as span:
            hits = self._retrieve(qvec, self.retrieve_k)
            span["top_doc"] = hits[0].doc_id if hits else None
        with stages("rerank", n_in=len(hits), n_out=k_final):
            final = hits[:k_final]       # no reranker in the shipped config (Lab 3)
        res.retrieved_docs = list(dict.fromkeys(h.doc_id for h in hits))

        with stages("generate", n_sources=len(final)):
            out = chat(self.build_prompt(clean, final), system=ANSWER_SYSTEM,
                       tier="MAIN", temperature=0.0, max_tokens=600, return_full=True)
        usage = out.get("usage", {})
        res.n_llm_calls = 1
        res.list_cost_usd = float(usage.get("cost_usd", 0.0) or 0.0)
        res.llm_latency_ms = float(usage.get("latency_ms", 0.0) or 0.0)
        res.cost_usd = 0.0 if usage.get("cached") else res.list_cost_usd
        self._charge(res.cost_usd)

        self._finish(res, (out.get("text") or "").strip(), final,
                     out.get("finish_reason"), stages)
        if use_cache:
            self._store(key, clean, qvec, k_final, mode, res)

    @staticmethod
    def _copy_cached(res: Result, hit: Result, layer: str) -> None:
        for f in ("answer", "refused", "valid", "citations", "sources",
                  "retrieved_docs", "invalid_citations"):
            setattr(res, f, getattr(hit, f))
        res.hits = list(hit.hits)
        res.cached, res.cache_layer, res.cost_usd = True, layer, 0.0
        res.list_cost_usd = 0.0

    # -- streaming (Part B2/B3) -------------------------------------------------
    def ask_stream(self, question: str, *, top_k: int | None = None) -> Iterator[dict]:
        """Yield SSE-ready events: meta -> token* -> validation -> done.

        B3 decision: *stream the prose, hold the verdict to the end*. Tokens go
        out immediately (TTFT is the whole point); the citation list and the
        validity verdict arrive in a final ``validation`` event carrying the
        authoritative answer. If validation fails, ``validation.answer`` is the
        refusal and ``validation.replace`` is true -- the UI overwrites what it
        streamed and says so. See the report for why not buffer-first.
        """
        t0 = time.perf_counter()
        k_final = top_k or self.final_k
        stages = _Stages()
        with tracing.trace("http.ask_stream", question=question[:120]) as root:
            res = Result(question=question, answer="", trace_id=root["span_id"])
            yield {"event": "meta", "trace_id": res.trace_id}
            clean, _, flags = self.guard_input(question)
            if flags:
                res.answer, res.refused, res.blocked = BLOCKED_MESSAGE, True, True
                yield {"event": "token", "text": BLOCKED_MESSAGE}
                yield self._final_event(res, t0, None, replace=False)
                return

            key = self._key(clean, k_final, "rag")
            hit = self._exact_get(key)
            if hit is not None:
                self.counters["exact_hits"] += 1
                self._copy_cached(res, hit, "exact")
                yield {"event": "token", "text": res.answer}
                yield self._final_event(res, t0, t0, replace=False)
                return

            self._check_budget()
            with stages("embed"):
                qvec = embed(clean, input_type="query")
            with stages("retrieve"):
                hits = self._retrieve(qvec, self.retrieve_k)
            final = hits[:k_final]
            prompt = self.build_prompt(clean, final)

            first_token_at: float | None = None
            parts: list[str] = []
            for piece, usage in self._generate_stream(prompt, stages):
                if piece:
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    parts.append(piece)
                    yield {"event": "token", "text": piece}
                if usage:
                    res.cost_usd = res.list_cost_usd = usage["cost_usd"]
            streamed = "".join(parts).strip()
            self._charge(res.cost_usd)
            self._finish(res, streamed, final, None, stages)
            res.stages = {k: round(v, 2) for k, v in stages.ms.items()}
            self.counters["misses"] += 1
            self._store(key, clean, qvec, k_final, "rag", res)
            yield self._final_event(res, t0, first_token_at,
                                    replace=res.answer != streamed)

    def _final_event(self, res: Result, t0: float, first_token_at: float | None,
                     replace: bool) -> dict:
        now = time.perf_counter()
        return {"event": "validation", "answer": res.answer, "replace": replace,
                "refused": res.refused, "valid": res.valid,
                "invalid_citations": res.invalid_citations,
                "citations": res.citations, "sources": res.sources,
                "cached": res.cached, "cost_usd": res.cost_usd,
                "ttft_ms": round(((first_token_at or now) - t0) * 1000, 1),
                "total_ms": round((now - t0) * 1000, 1),
                "stages": res.stages, "trace_id": res.trace_id}

    def _generate_stream(self, prompt: str, stages: _Stages
                         ) -> Iterator[tuple[str, dict | None]]:
        """Real token streaming online; chunked replay of the cached answer offline."""
        from aip import cost
        if settings.offline:
            with stages("generate"):
                out = chat(prompt, system=ANSWER_SYSTEM, tier="MAIN", temperature=0.0,
                           max_tokens=600, return_full=True)
            words = re.findall(r"\S+\s*", out["text"])
            for w in words:
                yield w, None
            yield "", {"cost_usd": 0.0}
            return

        from litellm import completion
        model = resolve_model("MAIN")
        t0 = time.perf_counter()
        pt = ct = 0
        with stages("generate"), tracing.trace("llm.stream", model=model, cached=False) as span:
            try:
                stream = completion(
                    model=model, temperature=0.0, max_tokens=600, stream=True,
                    stream_options={"include_usage": True},
                    messages=[{"role": "system", "content": ANSWER_SYSTEM},
                              {"role": "user", "content": prompt}],
                    timeout=settings.timeout_s)
                first = True
                for chunk in stream:
                    u = getattr(chunk, "usage", None)
                    if u:
                        pt = int(getattr(u, "prompt_tokens", 0) or 0)
                        ct = int(getattr(u, "completion_tokens", 0) or 0)
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        if first:
                            span["ttft_ms"] = round((time.perf_counter() - t0) * 1000, 1)
                            first = False
                        yield delta, None
            except BudgetExceeded:
                raise
            except Exception as exc:  # noqa: BLE001
                span["error_kind"] = type(exc).__name__
                if is_outage(exc):
                    raise UpstreamUnavailable(str(exc)[:200], retry_after(exc)) from exc
                raise
            usd = cost.price_of(model, pt, ct)
            span.update(prompt_tokens=pt, completion_tokens=ct, cost_usd=round(usd, 6),
                        latency_ms=round((time.perf_counter() - t0) * 1000, 1))
            cost.record(cost.Usage(model, pt, ct, usd, (time.perf_counter() - t0) * 1000,
                                   cached=False, calls=1, priced=cost.is_priced(model)))
        yield "", {"cost_usd": usd}

    # -- introspection ---------------------------------------------------------
    def stats(self) -> dict:
        c = self.counters
        total = c["exact_hits"] + c["semantic_hits"] + c["misses"]
        return {"chunks": self.n_chunks, "docs": self.n_docs,
                "exact_entries": len(self._exact), "semantic_entries": len(self._semantic),
                "semantic_threshold": self.threshold, "entity_guard": self.entity_guard,
                "hit_rate": round((c["exact_hits"] + c["semantic_hits"]) / total, 4) if total else 0.0,
                **c, "spent_today_usd": round(self.spent_today_usd, 6)}
