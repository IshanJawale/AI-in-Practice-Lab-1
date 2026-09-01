#!/usr/bin/env python3
"""Lab 1, Part A — the version everyone writes first.

Run it. Do not fix it. Characterise how it fails.

    python labs/lab1/v0_naive.py --n 40

This file is intentionally bad in ways that are intentionally realistic. Every
one of its problems has been shipped to production by someone with a job title
more senior than yours.

Read the output carefully. It is in two halves, and the second half is the
interesting one: a *single* trivial bug in `extract_v0` hides every other
defect in the model's output behind it. You cannot count what you cannot parse.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aip import chat  # noqa: E402
from aip.cost import Budget  # noqa: E402


PROMPT = """Extract the following from this support ticket and return JSON:
category, urgency, sentiment, policy_number, product.

Ticket:
{ticket}
"""

ALLOWED_CATEGORIES = {
    "billing", "claims", "policy_change", "technical",
    "complaint", "information", None,
}

FENCE = re.compile(r"```")


def extract_v0(ticket: str) -> dict:
    """The version everyone writes first. Do not fix this -- it is the exhibit."""
    out = chat(PROMPT.format(ticket=ticket), tier="SMALL", max_tokens=300)
    return json.loads(out)          # <-- failure mode 5, waiting to happen


# ---------------------------------------------------------------------------
# Diagnostics only. v0 does NOT do any of this -- that is the whole point.
# These two helpers exist so the report can tell you *why* the parse failed and
# *what was behind it*. Part B is where you earn the right to parse tolerantly.
# ---------------------------------------------------------------------------

def classify_parse_failure(raw: str) -> str:
    """Name the reason a bare json.loads() rejected this string."""
    if FENCE.search(raw):
        return "markdown_fence"
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            json.loads(raw[start : end + 1])
            return "prose_around_json"
        except json.JSONDecodeError:
            return "malformed_json"
    if start != -1:
        return "truncated_json"
    return "not_json_at_all"


def salvage(raw: str) -> dict | None:
    """Tolerantly recover the JSON object, the way Part B eventually will."""
    text = raw.strip()
    if FENCE.search(text):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def content_problems(rec: dict, ticket: str) -> list[str]:
    """The defects that live *inside* a successfully parsed object."""
    problems = []
    for f in ("category", "urgency", "sentiment", "policy_number", "product"):
        if f not in rec:
            problems.append(f"missing:{f}")
    if isinstance(rec.get("urgency"), str):
        problems.append("urgency_is_string")
    if rec.get("category") not in ALLOWED_CATEGORIES:
        problems.append("category_out_of_set")
    pn = rec.get("policy_number")
    if pn and str(pn) not in ticket:
        problems.append("policy_number_invented")
    return problems


def _tally(counter: Counter, examples: dict, key: str, ticket_id: str) -> None:
    counter[key] += 1
    examples.setdefault(key, ticket_id)


def _dump(title: str, counter: Counter, examples: dict) -> None:
    print(f"  {title}")
    if not counter:
        print("    (none)")
        return
    for k, v in counter.most_common():
        print(f"    {k:<26} {v:>3}   e.g. {examples[k]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    rows = [json.loads(l) for l in
            (root / "data/eval/extraction_dev.jsonl").open(encoding="utf-8")][: args.n]

    blocked: Counter[str] = Counter()      # why bare json.loads() refused
    hidden: Counter[str] = Counter()       # defects behind the parse failure
    crashed: Counter[str] = Counter()      # everything else
    ex_blocked: dict[str, str] = {}
    ex_hidden: dict[str, str] = {}
    ex_crashed: dict[str, str] = {}

    parsed_strict = 0
    parsed_salvaged = 0
    unsalvageable = 0
    ok = 0                                  # strict parse AND no content problems
    ok_if_fenceless = 0                     # would be clean if parsing were tolerant

    with Budget(limit_usd=0.10, label="lab1-v0") as b:
        for r in rows:
            ticket = r["input"]
            try:
                # extract_v0() inlined, so the report can see the raw string.
                raw = chat(PROMPT.format(ticket=ticket), tier="SMALL", max_tokens=300)
                print(raw)
            except Exception as exc:                      # noqa: BLE001
                _tally(crashed, ex_crashed, f"exception:{type(exc).__name__}", r["id"])
                continue

            try:
                rec = json.loads(raw)                     # exactly what v0 does
                parsed_strict += 1
                strict_ok = True
            except json.JSONDecodeError:
                _tally(blocked, ex_blocked, classify_parse_failure(raw), r["id"])
                rec = salvage(raw)
                strict_ok = False
                if rec is None:
                    unsalvageable += 1
                    continue
                parsed_salvaged += 1

            problems = content_problems(rec, ticket)
            for p in problems:
                _tally(hidden, ex_hidden, p, r["id"])
            if not problems:
                ok_if_fenceless += 1
                if strict_ok:
                    ok += 1

    n = len(rows)
    print(f"\n{'='*64}\nPART 1 — what v0 actually did\n{'='*64}")
    print(f"  bare json.loads() parsed      {parsed_strict:>3}/{n}")
    print(f"  clean records                 {ok:>3}/{n}")
    print()
    _dump("why the parse failed:", blocked, ex_blocked)
    if crashed:
        print()
        _dump("unhandled exceptions:", crashed, ex_crashed)

    print(f"\n{'='*64}\nPART 2 — what was hiding behind it\n{'='*64}")
    print("  Diagnostics only. v0 does none of this; Part B is where you earn it.")
    print(f"  recovered by stripping the wrapper   {parsed_salvaged:>3}")
    print(f"  unrecoverable even so                {unsalvageable:>3}")
    print(f"  would be clean if parsing were tolerant   {ok_if_fenceless:>3}/{n}")
    print()
    _dump("defects INSIDE the recovered JSON:", hidden, ex_hidden)

    print("\n" + b.report())
    print("\nNow answer, in your notes:")
    print("  1. Which of these are in the T1 §3 taxonomy, and which two are not?")
    print(f"  2. Fixing ONE line in extract_v0 takes you from {parsed_strict}/{n} parsed")
    print(f"     to {parsed_strict + parsed_salvaged}/{n} parsed -- but only {ok_if_fenceless}/{n} CLEAN.")
    print("     Why is that second number the entire justification for Part B?")
    print("  3. Which of these would a human reviewer even notice in production?")


if __name__ == "__main__":
    main()
