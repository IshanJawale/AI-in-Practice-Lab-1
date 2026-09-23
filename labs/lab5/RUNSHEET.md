# Lab 5 — Runsheet

**Follow this top to bottom.** Every step says *why*, *what*, *how*, and how you
know you are finished.

| | |
|---|---|
| [`OVERVIEW.md`](OVERVIEW.md) | **why** — read before the lab |
| [`README.md`](README.md) | **the brief** — targets, deliverables, rubric |
| [`CONCEPTS.md`](CONCEPTS.md) | **the reference** — concept → code → theory |
| [`CODE_GUIDE.md`](CODE_GUIDE.md) | **the file** — what is provided, every TODO |
| this file | **the actions** |

**Pairs.** Swap driver at each part.

---

## The lab in one line

> Your Lab 4 system gets about a quarter of the questions wrong. Find out
> *which stage* is failing, fix the biggest cluster, and prove what happened —
> including if the answer is "it got worse".

---

## ⚠️ Read this before anything else

**You are graded on the process, not the score.**

When the reference solution ran this lab it diagnosed the dominant cluster
correctly, chose a well-motivated fix, predicted 4–6 recoveries — and measured
**−0.050 correctness.** The fix made the system worse.

**That is a complete, full-marks Lab 5.** What is graded is whether you
diagnosed before you fixed, predicted before you measured, and reported what
happened rather than what you hoped. A **−0.05 you can explain scores above a
+0.12 you cannot.**

---

## Before you sit down

- [ ] **`reports/lab4.json` exists.** This is a hard prerequisite — Lab 5 reads it
- [ ] Your ten tagged failures from Lab 4 E3, in hand
- [ ] T4 §5 (the seven failure modes) re-read. The diagnostic tree especially
- [ ] `make check` clean

---

# 1 · Part A — classify every failure — 50 min

**Why.** *"RAG is bad"* is not a diagnosis. Exactly one stage failed on each
wrong answer. This part is most of the lab, and the rest depends on it.

**1.1 — `A1`.**

```bash
python labs/lab5/diagnose.py --input reports/lab4.json
```

The script automates what can be automated:

| Check | Automated | Decides |
|---|---|---|
| Is the answer in the corpus at all? | grep | Mode 1 |
| Is the gold chunk retrievable by its own text? | yes | Mode 3 vs 2 |
| Was the gold doc in the top 30? | yes | Mode 4 |
| Dropped by the reranker? | yes | Mode 5 |
| **Does gold context fix the answer?** | yes, one call | **Mode 6** |
| Right answer, wrong citation? | yes | Mode 7 |
| Did the answer straddle a chunk boundary? | **no — you look** | Mode 2 |

Produce the tally across all seven modes.

**1.2 — `A2`.** For every case marked `needs_human_check`, **open the chunks
around the gold answer and look.** Record your judgement *and your reason*.
This is the part no script can do.

**1.3 — `A3`.** `--pareto`. Name the two modes that account for most failures.

> ⚠️ **The one people get backwards.** Gold context **fixing** the answer means
> **RETRIEVAL** was at fault — the generator was always capable and was not
> given what it needed. Still wrong with gold context means **generation**.
>
> **Checkpoint.** A tally spread evenly across seven modes means you have
> mis-classified. Re-read the tree and re-check the mode-6 test.
>
> **A heavily concentrated tally is normal.** The reference, starting from Lab
> 3's *winning* retriever, found **13 of 14 failures in mode 6** and one in mode
> 4 — and its gold-context decomposition agreed independently. If you started
> from a weaker retriever you will see a different spread, **and that is exactly
> why you classify rather than guess.** Your backlog is yours.

---

# 2 · Part B — rank by expected value — 20 min

**Why.** The largest cluster is not always the right target.

**2.1** Build the table:

| Cluster | n | Fix | Est. recovery | Cost Δ | Latency Δ | Effort |
|---|---|---|---|---|---|---|

**2.2** Pick one. **Justify it in one sentence.** A cluster of 9 whose fix costs
3× per query may well lose to a cluster of 6 with a free fix.

**2.3 — write the prediction down, now, before you implement:**

> *"I expect this to recover **N** of the **M** failures in this cluster."*

> Being wrong is informative and is **not** penalised. **Not predicting is.**

---

# 3 · Part C — implement the fix — 70 min

**Why.** One change, measured, is worth more than three changes and a moved
number.

**3.1** Pick from the catalogue (README Part C) by **mode**, cheapest first.

**3.2 — three rules:**

1. **One fix at a time, measured each time.** Three fixes and a moved score
   teaches you nothing transferable.
2. **Record the failures too.** A fix that did not work, with the number
   showing it, is a result and scores marks.
3. **Fix what the diagnosis says, not what you reach for by reflex.**

> 📌 An earlier draft of the reference "fixed" retrieval — archived filter,
> wider `final_k` — after a tally saying 93% of failures were *generation*. It
> would have measured a change against a problem that was not there. **When your
> fix and your tally disagree, either the tally wins or the tally was wrong.
> Stop and resolve it.**

**3.3** The archived-document trap (Q29–Q31): if those still fail, the fix is
**metadata filtering**, not retrieval tuning, and it is essentially free. If you
did it in Lab 3, say so.

> **Cost discipline:** your fix must cost **≤ 2×** the Lab 4 baseline per query.

---

# 4 · Part D — prove it — 25 min

**4.1 — `D1`.** Before/after on the **same** questions, **every** Lab 4 metric —
not just the one you targeted:

| Metric | v1 | v2 | Δ |
|---|---|---|---|
| correctness · faithfulness · citation validity | | | |
| refusal recall / precision | | | |
| nDCG@10 / recall@5 | | | |
| cost per query · p95 latency | | | |

**4.2 — `D2`. The regression check. Report anything that got worse,
prominently.** Look specifically at:

- **refusal precision** — better retrieval often makes a system refuse *less*,
  which can make it answer unanswerable questions confidently
- **cost and p95** — HyDE and multi-query each add a call per query
- the question kinds that were already passing

**4.3 — `D3`.** Re-classify the *remaining* failures. Did the distribution shift
as you predicted?

> A fix that moves failures from mode 3 to mode 6 has not created a new problem
> — it has **revealed one that was previously masked.** That is progress. Say so.

**4.4 — `D4`.** State the next fix you would make, and what you expect it to be
worth.

---

# 5 · Show & tell — 4 minutes per pair

1. Your Pareto chart — 1 min
2. Your prediction, and what actually happened — 1 min
3. The regression: what got worse — 1 min
4. Questions — 1 min

---

## Deliverables checklist

- [ ] `labs/lab5/diagnose.py` with your classification and your fix
- [ ] `reports/lab5_before_after.json`
- [ ] `report.md` ≤ 3 pages:
  - [ ] the failure tally and the Pareto chart
  - [ ] the Part B ranking table + your one-sentence justification
  - [ ] **your prediction, and what actually happened**
  - [ ] the D1 before/after table
  - [ ] the D2 regression check, **including anything that got worse**
  - [ ] the D3 re-classification
  - [ ] **the fix that did not work**, with its number

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| `FileNotFoundError: reports/lab4.json` | Finish Lab 4 first. This is the input |
| Tally spread evenly across seven modes | Mis-classified. Re-check the mode-6 test |
| Everything lands in mode 6 | Normal if you started from a strong retriever |
| The fix helped but cost doubled | That is a result. Report it against the ≤2× rule |
| Correctness went down | **Report it.** That is a full-marks Lab 5 |

## The sentence to leave with

> ### Diagnose before you fix. Predict before you measure.
