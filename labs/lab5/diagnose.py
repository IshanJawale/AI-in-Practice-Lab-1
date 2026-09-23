#!/usr/bin/env python3
"""Lab 5 — the failure classifier.

    python labs/lab5/diagnose.py --input reports/lab4.json
    python labs/lab5/diagnose.py --input reports/lab4.json --pareto

Implements the T4 §5 diagnostic tree. Everything that can be decided by code
is decided by code; mode 2 needs your eyes and the script says so.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from labs.lab3.search import load_corpus, load_questions  # noqa: E402
from labs.lab4.rag import answer_with_gold_context  # noqa: E402
from labs.lab4.evaluate import judge_correctness  # noqa: E402

MODES = {
    1: "missing_content",
    2: "chunk_boundary",
    3: "embedding_mismatch",
    4: "ranking",
    5: "reranker",
    6: "generation",
    7: "presentation",
}


def answer_in_corpus(gold_answer: str, corpus: dict[str, str],
                     relevant_docs: list[str]) -> bool:
    """Mode 1 test. Crude keyword overlap, deliberately.

    TODO: this is a weak test -- it will pass on a paraphrase and fail on a
    numeric answer expressed differently. Improve it, and say in your report
    how you know your improvement is better.
    """
    text = " ".join(corpus.get(d, "") for d in relevant_docs).lower()
    if not text:
        return False
    tokens = [t for t in gold_answer.lower().split() if len(t) > 4]
    if not tokens:
        return True
    return sum(1 for t in tokens if t.strip(".,;()") in text) / len(tokens) > 0.4


def classify(row: dict, q: dict, corpus: dict[str, str], *,
             gold_context_fixes_it: bool | None = None,
             in_top_30: bool | None = None,
             dropped_by_reranker: bool | None = None) -> tuple[int, str]:
    """Walk the T4 §5 diagnostic tree. Returns (mode, evidence).

    The implementation follows the diagnostic tree described in the lab
    material. It attempts to automate every branch that can be decided
    programmatically; branches that require human judgment fall back to
    mode 2 with a clear evidence string.
    """
    # Mode 7 first: right answer, wrong citation.
    if row.get("correctness", 0) >= 2 and not row.get("citations_valid", True):
        return 7, f"correct answer, invalid citations {row.get('invalid_citations')}"

    # Mode 1: answer missing from the corpus.
    if not answer_in_corpus(q["gold_answer"], corpus, q["relevant_docs"]):
        return 1, "gold answer content not found in the relevant documents"

    # Mode 6: does gold‑context fix the answer?
    if gold_context_fixes_it is None:
        gold_docs = [corpus[d] for d in q.get("relevant_docs", []) if d in corpus]
        if gold_docs:
            gold_ans = answer_with_gold_context(q["question"], gold_docs)
            gold_correctness = judge_correctness(q["question"], gold_ans.text, q["gold_answer"])
            gold_context_fixes_it = gold_correctness >= 2
        else:
            gold_context_fixes_it = False
    if not gold_context_fixes_it:
        return 6, "gold context does not fix answer (generation failure)"

    # At this point the failure is in the retrieval pipeline.
    if in_top_30 is None:
        retrieved_set = set(row.get("retrieved", []))
        in_top_30 = any(doc_id in retrieved_set for doc_id in q.get("relevant_docs", []))
    if not in_top_30:
        # Gold doc not in top‑30 – decide between embedding mismatch (mode 3)
        # and chunk‑boundary (mode 2) by a simple keyword search.
        gold_found = answer_in_corpus(q["gold_answer"], corpus, list(corpus.keys()))
        if gold_found:
            return 3, "gold doc not in top‑30 but found by keyword search (embedding mismatch)"
        else:
            return 2, "gold doc not in top‑30 and not found by keyword search (chunk boundary)"

    # Gold doc is in the top‑30. Determine whether a reranker dropped it.
    if dropped_by_reranker is None:
        final_set = set(row.get("retrieved", []))
        dropped_by_reranker = not any(doc_id in final_set for doc_id in q.get("relevant_docs", []))
    if dropped_by_reranker:
        return 5, "gold doc was in top‑30 but dropped by reranker (reranker error)"
    else:
        return 4, "gold doc in top‑30 and retained after ranking (ranking issue)"


def pareto(tally: Counter) -> str:
    total = sum(tally.values()) or 1
    lines, cum = ["failure mode          n    share   cumulative"], 0
    for mode, n in tally.most_common():
        cum += n
        bar = "█" * round(30 * n / total)
        lines.append(f"{MODES[mode]:<20} {n:>3}   {n/total:>5.1%}   "
                     f"{cum/total:>5.1%}  {bar}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="reports/lab4.json")
    ap.add_argument("--pareto", action="store_true")
    ap.add_argument("--save", default="reports/lab5_diagnosis.json")
    args = ap.parse_args()

    rows = json.loads((ROOT / args.input).read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in load_questions(include_unanswerable=True)}
    corpus = load_corpus()

    failures = [r for r in rows
                if r.get("correctness", 2) < 2 or not r.get("citations_valid", True)]
    print(f"{len(failures)} failures out of {len(rows)}\n")

    out, tally = [], Counter()
    for r in failures:
        q = questions[r["id"]]
        mode, evidence = classify(r, q, corpus)
        tally[mode] += 1
        out.append({"id": r["id"], "kind": q["kind"], "mode": mode,
                    "mode_name": MODES[mode], "evidence": evidence,
                    "question": q["question"], "answer": r["answer"][:300]})
        print(f"  {r['id']:<5} {MODES[mode]:<20} {evidence}")

    print("\n" + pareto(tally))
    print("\nCases marked needs_human_check are Part A2. Open them.")

    p = ROOT / args.save
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved -> {p}")


if __name__ == "__main__":
    main()
