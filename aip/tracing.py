"""Minimal JSONL tracing.

Observability in one file. Every model call appends a record to
`.aip_traces/<run>.jsonl`. In Lab 7 you will read these back to build a
latency and cost dashboard; in Lab 5 you will read them to work out which
stage of your RAG pipeline produced a bad answer.

This is a teaching-scale stand-in for Langfuse / LangSmith / Phoenix. The
concept is identical: structured events, a run id, and a parent span id.
"""
from __future__ import annotations

import contextlib
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

from aip.config import settings

_LOCAL = threading.local()
RUN_ID = os.getenv("AIP_RUN_ID") or time.strftime("%Y%m%d-%H%M%S")
_TRACE_FILE: Path = settings.trace_dir / f"{RUN_ID}.jsonl"
_WRITE_LOCK = threading.Lock()


def _span_stack() -> list[dict[str, Any]]:
    if not hasattr(_LOCAL, "stack"):
        _LOCAL.stack = []
    return _LOCAL.stack


@contextlib.contextmanager
def trace(name: str, **attrs: Any) -> Iterator[dict[str, Any]]:
    """Open a span.

        with trace("retrieve", k=8) as span:
            docs = retriever.search(q, k=8)
            span["n_results"] = len(docs)
    """
    stack = _span_stack()
    span_id = uuid.uuid4().hex[:12]
    record: dict[str, Any] = {
        "run_id": RUN_ID,
        "span_id": span_id,
        "parent_id": stack[-1]["span_id"] if stack else None,
        "name": name,
        "ts": time.time(),
        **attrs,
    }
    stack.append(record)
    t0 = time.perf_counter()
    try:
        yield record
        record["status"] = "ok"
    except Exception as exc:  # noqa: BLE001 - we re-raise
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        record["duration_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        stack.pop()
        _write(record)


def event(name: str, **attrs: Any) -> None:
    """Record a point-in-time event with no duration."""
    stack = _span_stack()
    _write(
        {
            "run_id": RUN_ID,
            "span_id": uuid.uuid4().hex[:12],
            "parent_id": stack[-1]["span_id"] if stack else None,
            "name": name,
            "ts": time.time(),
            "duration_ms": 0.0,
            "status": "ok",
            **attrs,
        }
    )


def _write(record: dict[str, Any]) -> None:
    line = json.dumps(record, default=str)
    with _WRITE_LOCK:
        with _TRACE_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def read_traces(run_id: str | None = None) -> list[dict[str, Any]]:
    """Load one run's traces (default: the current run)."""
    path = settings.trace_dir / f"{run_id or RUN_ID}.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def trace_file() -> Path:
    return _TRACE_FILE
