# Lab 5 — RAG v2: Diagnose, Fix, Prove
**3 hours · Pairs · Prepared by T4 §5**

> **Read [`OVERVIEW.md`](OVERVIEW.md) first** — why this lab exists, how to
> approach the three hours, the hints, and the map back to the theory
> sessions. Keep [`CONCEPTS.md`](CONCEPTS.md) open while you work.
> This file is the detail.

---

## The problem

Your Lab 4 system gets roughly a quarter of the questions wrong.

The instinct at this point is to try things: bigger model, more chunks, a
different embedding. That is how teams spend six weeks and gain two points.

This lab teaches the alternative. **Every wrong answer has exactly one stage
that failed. Find it, count how often each stage is at fault, fix the biggest
cluster, and prove the fix with a before/after table.**

You are graded on the *process*, not the final score. A team that raises
correctness by 4 points and can show exactly which failure mode they eliminated
scores higher than a team that raises it by 12 points and cannot say why.

### Targets

| Requirement | Target |
|---|---|
| Failure classification | every Lab 4 failure classified into the 7 modes, with evidence |
| A prediction | stated **before** implementing: which cluster, how many recoveries |
| A measured before/after | on every Lab 4 metric, not just the one you targeted |
| Regression check | anything that got worse is reported, prominently |
| Cost discipline | your fix costs ≤ 2× the Lab 4 baseline per query |

**There is no improvement target, and that is deliberate.** When the reference
solution ran this lab it diagnosed the dominant cluster correctly, chose a
well-motivated fix, predicted it would recover 4–6 of 13 failures — and
measured **−0.050 correctness**. The fix made the system worse.

That is a complete and full-marks Lab 5. What is graded is whether you
diagnosed before you fixed, predicted before you measured, and reported what
happened rather than what you hoped. A student who reports a −0.05 with a clear
account of why scores above one who reports +0.12 they cannot explain.

---

## Timetable

| Time | Part | What you do |
|---|---|---|
| 0:00–0:50 | **A** | Classify every failure. This is most of the lab |
| 0:50–1:10 | **B** | Rank the clusters by expected value |
| 1:10–2:20 | **C** | Fix the top cluster. Then the second, if time |
| 2:20–2:45 | **D** | Prove it: before/after, regression check, cost |
| 2:45–3:00 | Show & tell | Your Pareto chart and your one fix |

---

## Part A — Classify every failure (50 min)

```bash
python labs/lab5/diagnose.py --input reports/lab4.json
```

The script automates what can be automated and leaves you the judgement calls.
For each failed question it establishes:

| Check | Automated? | Decides |
|---|---|---|
| Is the answer in the corpus at all? | grep — yes | Mode 1 |
| Is the gold chunk retrievable by its own text? | yes | Mode 3 vs 2 |
| Was the gold doc in the top 30? | yes | Mode 4 |
| Was it in the top 30 and dropped by the reranker? | yes | Mode 5 |
| Does gold context fix the answer? | yes (one call) | Mode 6 |
| Is the answer right but the citation wrong? | yes | Mode 7 |
| Did the answer straddle a chunk boundary? | **no — you look** | Mode 2 |

**A1.** Run it. Produce the tally:

```
mode 1  missing content     n = __
mode 2  chunk boundary      n = __
mode 3  embedding mismatch  n = __
mode 4  ranking             n = __
mode 5  reranker            n = __
mode 6  generation          n = __
mode 7  presentation        n = __
```

**A2.** The script cannot decide mode 2. For every case it marks
`needs_human_check`, open the chunks around the gold answer and look. Record
your judgement and your reason.

**A3.** Produce a Pareto chart (`--pareto`). You will almost certainly find
that two modes account for most failures. Name them.

> **Checkpoint.** If your tally is spread evenly across all seven modes, you
> have probably mis-classified. Re-read the diagnostic tree in T4 §5 and check
> the mode-6 test in particular — it is the one people get backwards. Gold
> context fixing the answer means **retrieval** was at fault, not generation.
>
> **A heavily concentrated tally is normal and is not a mistake.** The reference
> solution, starting from Lab 3's *winning* retrieval configuration, found 13 of
> 14 failures in mode 6 and one in mode 4. Its gold-context decomposition agreed
> independently: generation-attributable loss 0.107 against retrieval-attributable
> loss 0.071. If you started from a weaker retriever you will see a very
> different distribution — and *that is the point of classifying rather than
> guessing*. Your backlog is yours, not the reference's.

---

## Part B — Rank by expected value (20 min)

For each cluster, estimate:

| Cluster | n | Fix | Est. recovery | Cost delta | Latency delta | Effort |
|---|---|---|---|---|---|---|

Then pick. **Justify the pick in one sentence.** The largest cluster is not
always the right target — a cluster of 9 with a fix that costs 3× per query
may lose to a cluster of 6 with a free fix.

State your prediction *before* you implement: "I expect this to recover
N of the M failures in this cluster." At the end, compare your prediction to
what happened. Being wrong here is informative and is not penalised; not
predicting is.

---

## Part C — Implement the fix (70 min)

The catalogue, by mode. Pick from it or invent your own.

| Mode | Fixes, cheapest first |
|---|---|
| **1 Missing content** | There is no retrieval fix. Say so, and note what the corpus needs |
| **2 Chunk boundary** | Larger chunks · more overlap · markdown-aware · small-to-big (embed small, return parent) |
| **3 Embedding mismatch** | **Hybrid BM25+dense** · HyDE · multi-query · contextual retrieval |
| **4 Ranking** | Raise `final_k` · add a cross-encoder reranker · tune RRF weights |
| **5 Reranker** | Different reranker · always keep the top-1 from stage 1 · rerank only when the stage-1 margin is small |
| **6 Generation** | Fewer distractors in context · reorder so the best chunk is first or last, never middle · larger tier · a better prompt · decompose multi-hop questions |
| **7 Presentation** | Tighten the output contract · validate and repair citations · require the quoted span |

Two rules:

1. **One fix at a time, measured each time.** If you apply three fixes and the
   score moves, you have learned nothing transferable.
2. **Record the failures too.** A fix that did not work, with the number showing
   it did not, is a result and scores marks.
3. **Fix what the diagnosis says, not what you reach for by reflex.** An earlier
   draft of the reference solution "fixed" retrieval — an archived-document
   filter and a wider `final_k` — after a tally that said 93% of failures were
   generation. It would have measured a change against a problem that was not
   there. When your fix and your tally disagree, the tally wins or the tally was
   wrong; either way, stop and resolve it.

Special mention — **the archived-document trap** (Q29–Q31). If those are still
failing, the fix is metadata filtering, not retrieval tuning, and it is
essentially free. If you already did it in Lab 3, say so.

---

## Part D — Prove it (25 min)

**D1.** Before/after table on the same questions, every metric from Lab 4:

| Metric | v1 | v2 | Δ |
|---|---|---|---|
| correctness | | | |
| faithfulness | | | |
| citation validity | | | |
| refusal recall / precision | | | |
| nDCG@10 / recall@5 | | | |
| cost / query | | | |
| p95 latency | | | |

**D2 — the regression check.** Did anything get worse? Look specifically at:
- refusal precision (better retrieval often makes a system refuse *less*, which
  can make it answer unanswerable questions confidently)
- cost and p95 (HyDE and multi-query both add a call per query)
- the question kinds that were already passing

**D3.** Re-classify the *remaining* failures. Did the distribution shift as you
predicted? A fix that moves failures from mode 3 to mode 6 has not created a
new problem — it has revealed one that was previously masked, which is
progress. Say so if that is what happened.

**D4.** State the next fix you would make and what you expect it to be worth.

---

## Deliverables

1. `labs/lab5/diagnose.py` with your completed classification, and your fix
2. `report.md` — at most three pages:
   - the failure tally and the Pareto chart
   - your Part B ranking table and the justification for your pick
   - your prediction, and what actually happened
   - the D1 before/after table
   - the D2 regression check, including anything that got worse
   - the D3 re-classification
   - **the fix that did not work**, with its number
3. `reports/lab5_before_after.json`

---

## Rubric (9% of Module 1)

| Criterion | Weight | Full marks means |
|---|---|---|
| Diagnostic rigour | 35% | Every failure classified with evidence; mode-6 test done correctly |
| Prioritisation | 15% | Ranking by expected value, not by what seemed interesting |
| Fix quality | 20% | Implemented cleanly, measured, one variable at a time |
| Proof | 20% | Before/after complete; regression check genuine; nothing hidden |
| Honesty | 10% | Prediction stated up front; negative results reported |

---

## Stretch

1. **Automate mode 2.** Detect chunk-boundary failures by checking whether the
   gold answer span is split across chunks. Report your detector's precision
   against your hand labels from A2.
2. **Contextual retrieval** end to end, with the ingest cost measured.
3. **Multi-hop decomposition** for Q19–Q28. Measure on that subset only.
4. **Adaptive retrieval.** Route by query type: identifier → BM25, paraphrase →
   HyDE + dense, comparison → multi-query. Does routing beat one good pipeline?
5. **Ablation.** Remove each component of your final pipeline one at a time and
   report what each is actually worth. Some of them will be worth nothing.
