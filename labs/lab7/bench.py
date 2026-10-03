#!/usr/bin/env python3
"""Lab 7 / B2 + B4 — measure the running service: latency budget, caching, TTFT.

    # terminal 1 -- AIP_CACHE=0 so every uncached request really hits the network
    $env:AIP_CACHE="0"; uvicorn labs.lab7.service:app --port 8000
    # terminal 2
    python labs/lab7/bench.py --url http://localhost:8000 --n 20

Phases (sequential, so latency is not polluted by our own concurrency):
  1. cold      N golden questions, never seen -> uncached latency + stage budget
  2. repeat    the same N questions            -> exact-cache latency
  3. paraphrase hand-written rewordings        -> semantic-cache hits (and misses)
  4. stream    N further questions via /ask/stream -> TTFT vs total
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PARAPHRASES = [
    ("How many days do I have to submit a reimbursement claim after discharge?",
     "What is the deadline to file a reimbursement claim after I leave hospital?"),
    ("What is the room rent limit on the Silver plan?",
     "How much room rent per day does the Silver plan allow?"),
    ("What is the room rent limit on the Silver plan?",
     "What is the room rent limit on the Gold plan?"),         # near-miss: must NOT hit
]


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))], 1) if xs else 0.0


def ask(url: str, q: str) -> dict:
    t0 = time.perf_counter()
    r = requests.post(f"{url}/ask", json={"question": q}, timeout=120)
    wall = (time.perf_counter() - t0) * 1000
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    return {"status": r.status_code, "wall_ms": wall, **body}


def stream(url: str, q: str) -> dict:
    t0 = time.perf_counter()
    first, event, final = None, None, None
    with requests.post(f"{url}/ask/stream", json={"question": q}, stream=True, timeout=120) as r:
        for raw in r.iter_lines(decode_unicode=True):
            if raw.startswith("event:"):
                event = raw.split(":", 1)[1].strip()
            elif raw.startswith("data:"):
                if event == "token" and first is None:
                    first = (time.perf_counter() - t0) * 1000
                elif event == "validation":
                    final = json.loads(raw.split(":", 1)[1])
    total = (time.perf_counter() - t0) * 1000
    return {"client_ttft_ms": first, "client_total_ms": total, **(final or {})}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--save", default="reports/lab7_bench.json")
    a = ap.parse_args()

    from labs.lab3.search import load_questions
    qs = [q["question"] for q in load_questions(include_unanswerable=True)]
    cold_qs, stream_qs = qs[: a.n], qs[a.n: 2 * a.n]
    out: dict = {}

    print(f"health: {requests.get(a.url + '/health', timeout=30).json()['index']}")

    cold = [ask(a.url, q) for q in cold_qs]
    ok = [r for r in cold if r["status"] == 200]
    stages: dict[str, list[float]] = {}
    for r in ok:
        for k, v in r["stages_ms"].items():
            stages.setdefault(k, []).append(v)
    out["cold"] = {"n": len(cold), "errors": len(cold) - len(ok),
                   "p50_ms": pct([r["latency_ms"] for r in ok], 50),
                   "p95_ms": pct([r["latency_ms"] for r in ok], 95),
                   "cost_per_query_usd": round(statistics.fmean(r["cost_usd"] for r in ok), 6),
                   "stages": {k: {"p50": pct(v, 50), "p95": pct(v, 95)} for k, v in stages.items()},
                   "cached_flags": sum(r["cached"] for r in ok)}
    print("\nCOLD (uncached):", json.dumps(out["cold"], indent=2))

    rep = [ask(a.url, q) for q in cold_qs]
    out["repeat"] = {"n": len(rep),
                     "hit_rate": sum(r.get("cached", False) for r in rep) / len(rep),
                     "p50_ms": pct([r["latency_ms"] for r in rep if r["status"] == 200], 50),
                     "p95_ms": pct([r["latency_ms"] for r in rep if r["status"] == 200], 95),
                     "p95_wall_ms": pct([r["wall_ms"] for r in rep], 95),
                     "layers": sorted({r.get("cache_layer", "") for r in rep})}
    print("\nREPEAT (exact cache):", json.dumps(out["repeat"], indent=2))

    sem = []
    for base, variant in PARAPHRASES:
        ask(a.url, base)                       # make sure the base is cached
        r = ask(a.url, variant)
        sem.append({"base": base, "variant": variant, "cached": r.get("cached"),
                    "layer": r.get("cache_layer"), "latency_ms": r.get("latency_ms"),
                    "same_answer_as_base": r.get("answer") == ask(a.url, base).get("answer")})
    out["semantic"] = sem
    print("\nSEMANTIC:", json.dumps(sem, indent=2))

    st = [stream(a.url, q) for q in stream_qs]
    st = [s for s in st if s.get("client_ttft_ms") is not None]
    out["stream"] = {"n": len(st),
                     "ttft_p50_ms": pct([s["client_ttft_ms"] for s in st], 50),
                     "ttft_p95_ms": pct([s["client_ttft_ms"] for s in st], 95),
                     "total_p50_ms": pct([s["client_total_ms"] for s in st], 50),
                     "total_p95_ms": pct([s["client_total_ms"] for s in st], 95),
                     "replaced": sum(bool(s.get("replace")) for s in st)}
    print("\nSTREAM:", json.dumps(out["stream"], indent=2))

    p = ROOT / a.save
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nsaved -> {p}")


if __name__ == "__main__":
    main()
