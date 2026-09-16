#!/usr/bin/env python3
"""Generate filler documents so Lab 3 Part D can observe the ANN crossover.

The real corpus is 30 documents / a few hundred chunks. At that scale exact
NumPy search beats HNSW, and the interesting question -- where does approximate
search start to win? -- is invisible.

This script emits N deterministic filler documents into data/corpus_scaled/.
They are NOT used for quality metrics: they are lexically plausible insurance
prose with no golden answers in them, so they act purely as index ballast.

    python scripts/expand_corpus.py --docs 4000      # ~40k chunks

Then in Lab 3 D2, index data/corpus/ + data/corpus_scaled/ and time a query
under exact search and under HNSW. Report the crossover.
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/corpus_scaled"
SEED = 7

TOPICS = ["endorsement processing", "premium reconciliation", "surveyor appointment",
          "network empanelment", "policy issuance", "underwriting referral",
          "claim audit sampling", "branch reconciliation", "agent commission",
          "reinsurance treaty", "actuarial reserving", "IT change control",
          "vendor onboarding", "document retention", "call-centre quality",
          "fraud triage", "recovery and salvage", "arbitration procedure"]
REGIONS = ["North", "South", "East", "West", "Central", "North-East"]
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]

BODY = """\
## Scope

This standard operating procedure governs {topic} for the {region} region and
supersedes SOP-{code}-{prev}. It applies to all branches, the regional
processing centre, and empanelled third parties acting on Aurora's behalf.

## Responsibilities

The regional operations manager owns the process. The process owner reviews
exception reports weekly and escalates items ageing beyond {days} working days
to the functional head. Internal audit samples {pct}% of transactions quarterly.

## Procedure

1. The originating branch raises a request in the workflow system with all
   mandatory fields completed.
2. The processing centre acknowledges within {ack} working hours.
3. Where information is incomplete, a single consolidated query is raised.
   Piecemeal querying is not permitted.
4. Completed transactions are recorded in the register within {reg} working
   days and reconciled at month end.
5. Exceptions are logged with a root-cause code from the standard list.

## Turnaround standards

| Stage | Standard |
|---|---|
| Acknowledgement | {ack} working hours |
| First response | {days} working days |
| Closure | {close} working days |
| Escalation review | Weekly |

## Record retention

Records are retained for {ret} years from closure in accordance with the
group document retention schedule, after which they are destroyed under
dual control with a certificate of destruction.

## Review

This procedure is reviewed annually, or earlier on a regulatory change, a
material audit finding, or a system replacement.
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=int, default=2000)
    args = ap.parse_args()

    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.md"):
        p.unlink()

    for i in range(args.docs):
        topic = rng.choice(TOPICS)
        region = rng.choice(REGIONS)
        year = rng.choice(YEARS)
        code = f"{rng.randint(100, 999)}"
        text = (f"# SOP-{code}-{year}: {topic.title()} ({region} Region)\n\n"
                + BODY.format(topic=topic, region=region, code=code, prev=year - 1,
                              days=rng.choice([2, 3, 5, 7]), pct=rng.choice([2, 5, 10]),
                              ack=rng.choice([4, 8, 24]), reg=rng.choice([1, 2, 3]),
                              close=rng.choice([7, 10, 15, 21]),
                              ret=rng.choice([5, 7, 8, 10])))
        (OUT / f"sop-{i:05d}-{code}-{year}.md").write_text(text, encoding="utf-8")

    print(f"wrote {args.docs} filler documents to {OUT}")
    print("These are index ballast only. Do NOT include them when reporting")
    print("retrieval quality -- they contain no golden answers and would")
    print("flatter your metrics by making the corpus artificially easy to rank.")


if __name__ == "__main__":
    main()
