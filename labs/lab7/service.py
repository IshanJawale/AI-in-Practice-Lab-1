#!/usr/bin/env python3
"""Lab 7 — the service.

    uvicorn labs.lab7.service:app --reload --port 8000
    curl -s localhost:8000/ask -H 'content-type: application/json' \
         -d '{"question":"How long do I have to file a claim?"}' | jq
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aip import cache, tracing  # noqa: E402
from aip.config import settings  # noqa: E402
from aip.cost import BudgetExceeded, global_budget  # noqa: E402
from aip.guards import ToolGuard  # noqa: E402
from labs.lab7.pipeline import (  # noqa: E402
    AskPipeline,
    Result,
    UpstreamUnavailable,
    is_outage,
    retry_after,
)

_PIPELINE: AskPipeline | None = None
_STARTED = time.time()
_BUILD_LOCK = threading.Lock()


def pipeline() -> AskPipeline:
    """A2: the Labs 3-5 pipeline with the Lab 6 guards, built once and cached.

    Called from the lifespan hook so the corpus is embedded before the first
    request, and lazily here as a fallback (tests, `uvicorn --reload` workers).
    Building per request would re-embed the corpus on every call.
    """
    global _PIPELINE
    if _PIPELINE is None:
        with _BUILD_LOCK:
            if _PIPELINE is None:
                _PIPELINE = AskPipeline()
    return _PIPELINE


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(pipeline)
    yield


app = FastAPI(title="Aurora Policy Assistant", version="1.0", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    # None -> the pipeline default (final_k=10, the Lab 5 winner). A fixed
    # default of 5 here would silently serve a worse config than the gate measures.
    top_k: int | None = Field(default=None, ge=1, le=20)
    mode: str = Field(default="rag", pattern="^(rag|tools)$")


class Citation(BaseModel):
    index: int
    doc_id: str
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    refused: bool
    citations: list[Citation]
    sources: list[str] = []
    latency_ms: float
    cost_usd: float
    cached: bool
    trace_id: str
    cache_layer: str = ""
    stages_ms: dict[str, float] = {}


# ---------------------------------------------------------------------------
# error handling (A3)
# ---------------------------------------------------------------------------
def to_http_error(exc: Exception) -> HTTPException:
    """Map an internal failure to the status code that tells the caller what to do.

    429  budget exhausted        -> back off (Retry-After: the budget window is a day)
    503  provider outage/limit   -> retry soon; Retry-After says when
    500  anything else           -> generic body: no stack trace, no internals
    """
    if isinstance(exc, BudgetExceeded):
        return HTTPException(429, detail=f"budget exhausted: {exc}",
                             headers={"Retry-After": "3600"})
    if is_outage(exc):
        return HTTPException(503, detail="upstream model unavailable; retry shortly",
                             headers={"Retry-After": str(retry_after(exc))})
    return HTTPException(500, detail="internal error; quote the trace_id when reporting")


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
    http = to_http_error(exc)
    return JSONResponse({"detail": http.detail}, status_code=http.status_code,
                        headers=http.headers)


def _run_tools(question: str) -> Result:
    """mode='tools': the Lab 6 agent, with the Lab 6 guards (L1 delimit, L2 heuristic,
    L4 privilege capping -- issue_refund is not on the allowlist -- and L5 output filter)."""
    from labs.lab6.agent import REGISTRY, run_agent

    t0 = time.perf_counter()
    guard = ToolGuard(max_calls=6, allow=set(REGISTRY) - {"issue_refund"})
    with tracing.trace("http.ask", question=question[:120], mode="tools") as root:
        before = global_budget().spent_usd
        out = run_agent(question, guard=guard, layers=[1, 2, 5])
        stopped = out["stopped_because"]
        if stopped == "budget_exceeded":
            raise BudgetExceeded("per-request tool-loop budget exceeded")
        if stopped.startswith("error"):
            raise UpstreamUnavailable(stopped)
        cost = max(0.0, global_budget().spent_usd - before)
        ans = out["answer"] or "I could not complete that request."
        res = Result(question=question, answer=ans, refused=ans.startswith("BLOCKED"),
                     cost_usd=round(cost, 6), trace_id=root["span_id"],
                     latency_ms=round((time.perf_counter() - t0) * 1000, 2))
        root.update(cached=False, cost_usd=res.cost_usd, refused=res.refused,
                    latency_ms=res.latency_ms, tool_calls=len(out["tool_log"]))
    return res


def _to_response(r: Result) -> AskResponse:
    return AskResponse(
        answer=r.answer, refused=r.refused,
        citations=[Citation(**c) for c in r.citations], sources=r.sources,
        latency_ms=r.latency_ms, cost_usd=round(r.cost_usd, 6), cached=r.cached,
        trace_id=r.trace_id, cache_layer=r.cache_layer, stages_ms=r.stages)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """A1. Return cost and trace_id in the response -- they are how anyone
    debugging this later finds the trace and sees what the query cost."""
    try:
        if req.mode == "tools":
            return _to_response(_run_tools(req.question))
        return _to_response(pipeline().ask(req.question, top_k=req.top_k))
    except HTTPException:
        raise
    except Exception as exc:                                     # noqa: BLE001
        http = to_http_error(exc)
        tracing.event("http.error", status=http.status_code,
                      error_type=type(exc).__name__, error=str(exc)[:200])
        raise http from exc


# ---------------------------------------------------------------------------
# streaming (B2 / B3)
# ---------------------------------------------------------------------------
@app.post("/ask/stream")
async def ask_stream(req: AskRequest):
    """Server-sent events: `meta`, many `token`, then one `validation`.

    The pipeline generator runs in ONE worker thread and hands events to the
    event loop through a queue: tracing spans use thread-local stacks, so the
    spans opened inside the generator must open and close in the same thread.
    """
    pipe = await asyncio.to_thread(pipeline)
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue()
    DONE = object()

    def work() -> None:
        try:
            for ev in pipe.ask_stream(req.question, top_k=req.top_k):
                loop.call_soon_threadsafe(q.put_nowait, ev)
        except Exception as exc:                                  # noqa: BLE001
            http = to_http_error(exc)
            tracing.event("http.error", status=http.status_code,
                          error_type=type(exc).__name__, error=str(exc)[:200])
            loop.call_soon_threadsafe(q.put_nowait, {
                "event": "error", "status": http.status_code, "detail": http.detail})
        finally:
            loop.call_soon_threadsafe(q.put_nowait, DONE)

    threading.Thread(target=work, daemon=True).start()

    async def gen():
        while True:
            ev = await q.get()
            if ev is DONE:
                return
            name = ev.pop("event")
            yield {"event": name, "data": json.dumps(ev)}

    return EventSourceResponse(gen())


# ---------------------------------------------------------------------------
# health + metrics (C2)
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    p = pipeline()
    return {"status": "ok", "uptime_s": round(time.time() - _STARTED, 1),
            "index": {"docs": p.n_docs, "chunks": p.n_chunks,
                      "build_seconds": round(p.build_seconds, 1)},
            "models": settings.models, "profile": settings.profile,
            "offline": settings.offline, "cache": cache.stats(),
            "response_cache": p.stats()}


def _pctl(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))], 1)


def _today_spans() -> list[dict]:
    """Spans from every trace file written today (survives restarts)."""
    day = time.strftime("%Y%m%d")
    spans: list[dict] = []
    for path in sorted(settings.trace_dir.glob(f"{day}-*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            spans.extend(json.loads(l) for l in fh if l.strip())
    return spans


def summarise(spans: list[dict]) -> dict:
    """Pure function over spans so the dashboard, the tests and /metrics agree."""
    reqs = [s for s in spans if s.get("name") in ("http.ask", "http.ask_stream")]
    errors = [s for s in spans if s.get("name") == "http.error"]
    lat_all = [s["duration_ms"] for s in reqs]
    lat_hit = [s["duration_ms"] for s in reqs if s.get("cached")]
    lat_miss = [s["duration_ms"] for s in reqs if not s.get("cached") and not s.get("blocked")]
    cost = sum(float(s.get("cost_usd") or 0.0) for s in reqs)
    by_type: dict[str, int] = {}
    for e in errors:
        key = f"{e.get('status')}:{e.get('error_type')}"
        by_type[key] = by_type.get(key, 0) + 1
    tools: dict[str, int] = {}
    for s in spans:
        if s.get("name") == "tool.call":
            tools[s.get("tool", "?")] = tools.get(s.get("tool", "?"), 0) + 1
    answered = [s for s in reqs if not s.get("blocked")]
    n = len(reqs)
    return {
        "requests": n,
        "cost_today_usd": round(cost, 6),
        "cost_per_query_usd": round(cost / n, 6) if n else 0.0,
        "cache_hit_rate": round(sum(1 for s in reqs if s.get("cached")) / n, 4) if n else 0.0,
        "refusal_rate": round(sum(1 for s in answered if s.get("refused")) / len(answered), 4)
        if answered else 0.0,
        "latency_ms": {"p50": _pctl(lat_all, 50), "p95": _pctl(lat_all, 95),
                       "p99": _pctl(lat_all, 99)},
        "latency_cached_ms": {"p50": _pctl(lat_hit, 50), "p95": _pctl(lat_hit, 95)},
        "latency_uncached_ms": {"p50": _pctl(lat_miss, 50), "p95": _pctl(lat_miss, 95)},
        "errors": {"total": len(errors), "rate": round(len(errors) / (n + len(errors)), 4)
                   if (n + len(errors)) else 0.0, "by_type": by_type},
        "tool_calls": tools,
        "mean_latency_ms": round(statistics.fmean(lat_all), 1) if lat_all else 0.0,
    }


@app.get("/metrics")
def metrics() -> dict:
    """C2: cost today, cost/query, cache hit rate, p50/p95/p99, errors by type, tool calls."""
    b = global_budget()
    out = summarise(_today_spans())
    out["process"] = {**b.as_dict(), "p99_latency_ms": round(b.percentile(99), 1)}
    out["pipeline"] = pipeline().stats() if _PIPELINE else {}
    return out


@app.get("/trace/{trace_id}")
def get_trace(trace_id: str) -> dict:
    """C1: every span under one request, so 'why did X take 9 s?' is one curl."""
    spans = tracing.read_traces()
    by_parent: dict[str, list[dict]] = {}
    for s in spans:
        by_parent.setdefault(s.get("parent_id") or "", []).append(s)
    root = next((s for s in spans if s["span_id"] == trace_id), None)
    if root is None:
        raise HTTPException(404, detail="unknown trace_id (traces are per process run)")
    out, stack = [root], [trace_id]
    while stack:
        for child in by_parent.get(stack.pop(), []):
            out.append(child)
            stack.append(child["span_id"])
    out.sort(key=lambda s: s["ts"])
    slowest = max(out[1:], key=lambda s: s.get("duration_ms", 0), default=None)
    return {"trace_id": trace_id, "total_ms": root.get("duration_ms"),
            "slowest_span": slowest and {"name": slowest["name"],
                                          "duration_ms": slowest.get("duration_ms")},
            "spans": out}
