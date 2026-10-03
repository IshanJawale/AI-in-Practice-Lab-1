#!/usr/bin/env python3
"""Lab 7 — the regression gate. Exits non-zero when a threshold is breached.

    python labs/lab7/gate.py --config labs/lab7/thresholds.yml

It runs the *same* ``AskPipeline`` the service serves, over the whole golden
set (45 questions, 5 unanswerable), and judges it with the Lab 4 judges.

Reproducibility. With AIP_OFFLINE=1 every model call replays from the committed
cache, so CI needs no key and costs nothing. A replayed call reports $0 and 0 ms
to the live meters, which would make the cost and latency gates vacuous -- so
this script reads the *recorded* cost and generation latency out of the cache
entry instead, and adds the (real, measured) non-model stage time on top. The
latency it gates is therefore "recorded model time + measured local time".

Deliberate-break knobs (Part D3), read from the environment:
    AIP_GATE_FINAL_K=1        pass one chunk to the generator instead of ten
    AIP_GATE_DROP_DOC=<id>    delete a corpus document before indexing
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ["AIP_CACHE"] = "1"      # the gate is meaningless without the cache; .env says 0

import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _percentile(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))] if xs else 0.0


def measure(limit: int | None = None, save: str = "reports/lab7_gate.json"
            ) -> dict[str, float]:
    """D1: run the golden set through the service pipeline and return the metrics."""
    from aip.config import resolve_model
    from aip.cost import price_of
    from aip.evals import retrieval_metrics
    from aip.retrieval import format_context
    from labs.lab3.search import load_questions
    from labs.lab4.evaluate import judge_correctness, judge_faithfulness
    from labs.lab7 import pipeline as P

    drop = os.getenv("AIP_GATE_DROP_DOC")
    if drop:
        real = P.load_corpus
        P.load_corpus = lambda: {k: v for k, v in real().items() if k != drop}
    final_k = int(os.getenv("AIP_GATE_FINAL_K", P.FINAL_K))
    pipe = P.AskPipeline(final_k=final_k)

    questions = load_questions(include_unanswerable=True)
    if limit:
        questions = questions[:limit]
    embed_model = resolve_model("EMBED")

    def run(q: dict) -> dict:
        r = pipe.ask(q["question"], use_cache=False)
        ctx = format_context(r.hits)
        unanswerable = not q["relevant_docs"] or q["kind"] == "unanswerable"
        local_ms = sum(v for k, v in r.stages.items() if k != "generate")
        embed_cost = price_of(embed_model, math.ceil(len(q["question"]) / 4), 0)
        rm = retrieval_metrics(r.retrieved_docs, q["relevant_docs"], ks=(5,)) \
            if q["relevant_docs"] else None
        return {
            "id": q["id"], "kind": q["kind"], "unanswerable": unanswerable,
            "answer": r.answer, "refused": r.refused, "citations_valid": r.valid,
            "invalid_citations": r.invalid_citations,
            "faithfulness": judge_faithfulness(r.answer, ctx),
            "correctness": judge_correctness(q["question"], r.answer, q["gold_answer"]),
            "hit_rate_at_5": rm["hit_rate@5"] if rm else None,
            "retrieved": [h.doc_id for h in r.hits], "relevant": q["relevant_docs"],
            "cost_usd": r.list_cost_usd + embed_cost,
            "latency_ms": local_ms + r.llm_latency_ms,
            "stages_ms": r.stages, "llm_latency_ms": r.llm_latency_ms,
        }

    workers = int(os.getenv("AIP_GATE_WORKERS", "4"))
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(run, questions))
    wall = time.perf_counter() - t0

    ans = [r for r in rows if not r["unanswerable"]]
    una = [r for r in rows if r["unanswerable"]]
    refusals = [r for r in rows if r["refused"]]
    hit = [r["hit_rate_at_5"] for r in rows if r["hit_rate_at_5"] is not None]
    m = {
        "correctness": statistics.fmean(r["correctness"] for r in ans) / 2,
        "faithfulness": statistics.fmean(r["faithfulness"] for r in rows),
        "citation_validity": statistics.fmean(float(r["citations_valid"]) for r in rows),
        "refusal_recall": (sum(r["refused"] for r in una) / len(una)) if una else 0.0,
        "refusal_precision": (sum(r["unanswerable"] for r in refusals) / len(refusals))
        if refusals else 1.0,
        "hit_rate_at_5": statistics.fmean(hit),
        "cost_per_query_usd": statistics.fmean(r["cost_usd"] for r in rows),
        "p95_latency_ms": _percentile([r["latency_ms"] for r in rows], 95),
    }
    extra = {"p50_latency_ms": _percentile([r["latency_ms"] for r in rows], 50),
             "n": len(rows), "n_answerable": len(ans), "n_unanswerable": len(una),
             "n_refusals": len(refusals), "final_k": final_k, "dropped_doc": drop,
             "wall_seconds": round(wall, 1), "offline": os.getenv("AIP_OFFLINE", "0")}
    if save:
        p = ROOT / save
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"metrics": m, "run": extra, "rows": rows},
                                indent=2, ensure_ascii=False), encoding="utf-8")
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="labs/lab7/thresholds.yml")
    ap.add_argument("--limit", type=int, default=None, help="first N questions (smoke test)")
    ap.add_argument("--save", default="reports/lab7_gate.json")
    args = ap.parse_args()

    thresholds = yaml.safe_load((ROOT / args.config).read_text(encoding="utf-8"))
    try:
        metrics = measure(args.limit, args.save)
    except Exception as exc:                                    # noqa: BLE001
        # A gate that crashes must be red, and must say why. CacheMiss means the
        # committed cache no longer covers the pipeline's prompts.
        print(f"GATE ERROR: {type(exc).__name__}: {str(exc)[:600]}")
        if "CacheMiss" in type(exc).__name__:
            print("The committed cache does not cover this pipeline. Run the gate "
                  "once online (without AIP_OFFLINE) and commit .aip_cache/.")
        return 2

    failures = []
    width = max(len(k) for k in thresholds)
    print(f"{'metric':<{width}}  {'value':>10}  {'gate':>14}  status")
    print("-" * (width + 40))
    for name, rule in thresholds.items():
        value = metrics.get(name)
        if value is None:
            failures.append(f"{name}: not measured")
            print(f"{name:<{width}}  {'—':>10}  {'':>14}  MISSING")
            continue
        ok, gate = True, ""
        if "min" in rule:
            gate, ok = f">= {rule['min']}", value >= rule["min"]
        if "max" in rule and ok:
            gate, ok = f"<= {rule['max']}", value <= rule["max"]
        if not ok:
            failures.append(f"{name}: {value} violates {gate}")
        print(f"{name:<{width}}  {value:>10.4f}  {gate:>14}  {'ok' if ok else 'FAIL'}")

    if failures:
        print("\nGATE FAILED:")
        for f in failures:
            print("  " + f)
        return 1
    print("\nGATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
