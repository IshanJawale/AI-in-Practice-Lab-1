#!/usr/bin/env python3
"""Lab 7 / B1 — find the cosine threshold at which the semantic cache goes wrong.

    python labs/lab7/semantic_cache_sweep.py

Method. Hand-built question pairs over the Aurora corpus, labelled by whether
the *correct answer* is the same:

  * PARAPHRASE pairs  -- same question, different words. A cache SHOULD hit.
  * NEAR-MISS pairs   -- same words, different plan / number / condition, so a
                         different answer. A cache MUST NOT hit.

For every pair we compute the cosine similarity of the two query embeddings
(the same embedding the service uses). A *wrong hit* at threshold t is a
near-miss pair with cosine >= t: the cache would return the first question's
answer to the second. The highest near-miss similarity is therefore the
threshold the cache "starts returning wrong answers" at; any t at or below it
is unsafe. Labels are mine, not the model's, and the set is small -- the report
says so.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("AIP_CACHE", "1")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from aip.embed import embed_batch  # noqa: E402
from labs.lab7.pipeline import _discriminators  # noqa: E402

PARAPHRASE = [
    ("How many days do I have to submit a reimbursement claim after discharge?",
     "What is the deadline for filing a reimbursement claim after leaving hospital?"),
    ("What is the room rent limit on the Silver plan?",
     "How much room rent does the Silver plan allow per day?"),
    ("Is maternity covered under the Gold plan?",
     "Does the Gold plan include maternity benefits?"),
    ("How do I file a complaint about a rejected claim?",
     "What is the process to raise a grievance over a claim rejection?"),
    ("Can I port my policy to Aurora from another insurer?",
     "How does policy portability from a different insurer work?"),
    ("What is the waiting period for pre-existing conditions?",
     "How long must I wait before pre-existing conditions are covered?"),
    ("Does Aurora have cashless treatment at network hospitals?",
     "Can I get cashless hospitalisation at a network hospital?"),
    ("What is the grace period for paying my life insurance premium?",
     "How long is the grace period on a life insurance premium payment?"),
    ("Which documents are required to submit a claim?",
     "What paperwork do I need for filing a claim?"),
    ("Are dependent parents covered on the family floater?",
     "Can I add my parents to a family floater plan?"),
    ("What is excluded from travel insurance?",
     "What does the travel insurance policy not cover?"),
    ("How do I renew my policy?",
     "What are the steps for policy renewal?"),
]

NEAR_MISS = [
    ("What is the room rent limit on the Silver plan?",
     "What is the room rent limit on the Gold plan?"),
    ("What is the room rent limit on the Silver plan?",
     "What is the room rent limit on the Bronze plan?"),
    ("Is maternity covered under the Gold plan?",
     "Is maternity covered under the Silver plan?"),
    ("What is the waiting period on the Gold plan?",
     "What is the waiting period on the Silver plan?"),
    ("How many days do I have to submit a reimbursement claim after discharge?",
     "How many days do I have to submit a reimbursement claim before admission?"),
    ("What is the sum insured on the Platinum plan?",
     "What is the sum insured on the Bronze plan?"),
    ("What is the claim deadline for health insurance?",
     "What is the claim deadline for motor insurance?"),
    ("What is the grace period for a monthly premium?",
     "What is the grace period for an annual premium?"),
    ("What is the co-payment for senior citizens above 60?",
     "What is the co-payment for senior citizens above 75?"),
    ("Does the Silver plan cover dental treatment?",
     "Does the Silver plan exclude dental treatment?"),
    ("Is a pre-authorisation required for planned hospitalisation?",
     "Is a pre-authorisation required for emergency hospitalisation?"),
    ("What is the maximum cashless limit for a 2-member family?",
     "What is the maximum cashless limit for a 5-member family?"),
    ("Are pre-existing conditions covered after 2 years?",
     "Are pre-existing conditions covered after 4 years?"),
    ("What is the ombudsman office for Mumbai?",
     "What is the ombudsman office for Chennai?"),
    ("Is the critical illness rider available on the Gold plan?",
     "Is the critical illness rider available on the Bronze plan?"),
    ("What is the premium for a 35 year old on the Silver plan?",
     "What is the premium for a 55 year old on the Silver plan?"),
]


def main() -> None:
    allq = sorted({q for pair in PARAPHRASE + NEAR_MISS for q in pair})
    vecs = dict(zip(allq, embed_batch(allq, input_type="query")))

    def sims(pairs):
        return [float(vecs[a] @ vecs[b]) for a, b in pairs]

    sp, sn = sims(PARAPHRASE), sims(NEAR_MISS)
    guard_blocks = [_discriminators(a) != _discriminators(b) for a, b in NEAR_MISS]

    print(f"{'pair':<7}{'cosine':>8}   question pair")
    for label, pairs, ss in (("PARA", PARAPHRASE, sp), ("MISS", NEAR_MISS, sn)):
        for (a, b), s in sorted(zip(pairs, ss), key=lambda t: -t[1]):
            print(f"{label:<7}{s:>8.4f}   {a[:48]!r} | {b[:48]!r}")

    print(f"\nparaphrase  min={min(sp):.4f} median={np.median(sp):.4f} max={max(sp):.4f}")
    print(f"near-miss   min={min(sn):.4f} median={np.median(sn):.4f} max={max(sn):.4f}")
    print(f"\n{'threshold':>9}  {'paraphrase hits':>16}  {'WRONG hits':>11}  {'(entity guard)':>14}")
    rows = []
    for t in (0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92, 0.91, 0.90, 0.88, 0.85, 0.80):
        ph = sum(s >= t for s in sp)
        wr = sum(s >= t for s in sn)
        wr_guard = sum(1 for s, g in zip(sn, guard_blocks) if s >= t and not g)
        rows.append({"threshold": t, "paraphrase_hits": ph, "n_paraphrase": len(sp),
                     "wrong_hits": wr, "n_near_miss": len(sn),
                     "wrong_hits_with_entity_guard": wr_guard})
        print(f"{t:>9.2f}  {ph:>10}/{len(sp):<5}  {wr:>6}/{len(sn):<4}  {wr_guard:>9}/{len(sn)}")

    breaking = max(sn)
    print(f"\nFirst wrong hit appears at cosine {breaking:.4f}: any threshold <= that value "
          f"returns a wrong cached answer for at least one pair.")
    safe = next((r["threshold"] for r in rows if r["wrong_hits"] == 0), None)
    print(f"Lowest swept threshold with zero wrong hits: {safe}")
    out = ROOT / "reports" / "lab7_semantic_cache.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "embedding_model": os.getenv("AIP_PROFILE", "gemini"),
        "paraphrase": [{"a": a, "b": b, "cosine": s} for (a, b), s in zip(PARAPHRASE, sp)],
        "near_miss": [{"a": a, "b": b, "cosine": s, "entity_guard_blocks": g}
                      for (a, b), s, g in zip(NEAR_MISS, sn, guard_blocks)],
        "sweep": rows, "first_wrong_hit_cosine": breaking,
        "lowest_zero_wrong_threshold": safe}, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
