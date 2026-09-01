"""Content-addressed disk cache for model calls.

Why this exists
---------------
An LLM call is an expensive, slow, non-deterministic function. Almost every
painful thing about developing against one goes away if you make repeated
identical calls free and instant:

* You can re-run a 200-item extraction loop while debugging your parser
  without paying 200 times.
* Your eval harness becomes reproducible: same inputs, same outputs, so a
  diff in your score is a diff in *your code*, not model sampling noise.
* Grading and demos work offline (AIP_OFFLINE=1).

The cache key is a hash of everything that could change the output: model,
messages, temperature, tools, response format, seed. Change any of them and
you get a miss, as you should.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from typing import Any

from aip.config import settings

_LOCK = threading.Lock()
_DB_PATH = settings.cache_dir / "calls.sqlite3"


class CacheMiss(RuntimeError):
    """Raised in offline mode when a request has no cached response."""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS calls (
               key TEXT PRIMARY KEY,
               kind TEXT NOT NULL,
               request TEXT NOT NULL,
               response TEXT NOT NULL,
               created_at REAL NOT NULL
           )"""
    )
    return conn


def make_key(kind: str, payload: dict[str, Any]) -> str:
    """Stable hash of a request payload. Sorted keys so dict order is irrelevant."""
    blob = json.dumps({"kind": kind, **payload}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def get(key: str) -> dict[str, Any] | None:
    if not settings.cache_enabled:
        return None
    with _LOCK, _connect() as conn:
        row = conn.execute("SELECT response FROM calls WHERE key = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def put(key: str, kind: str, request: dict[str, Any], response: dict[str, Any]) -> None:
    if not settings.cache_enabled:
        return
    import time

    with _LOCK, _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO calls (key, kind, request, response, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                key,
                kind,
                json.dumps(request, default=str)[:200_000],
                json.dumps(response, default=str),
                time.time(),
            ),
        )


def stats() -> dict[str, int]:
    with _LOCK, _connect() as conn:
        rows = conn.execute("SELECT kind, COUNT(*) FROM calls GROUP BY kind").fetchall()
    return {kind: n for kind, n in rows}


def clear(kind: str | None = None) -> int:
    """Drop cached entries. Returns the number removed. Use with care."""
    with _LOCK, _connect() as conn:
        if kind:
            cur = conn.execute("DELETE FROM calls WHERE kind = ?", (kind,))
        else:
            cur = conn.execute("DELETE FROM calls")
        return cur.rowcount
