# Lab 3 — Runsheet

**Follow this top to bottom.** Every step says *why* it exists, *what* to do,
*how* to do it, and how you know you are finished.

Four documents, four jobs:

| | |
|---|---|
| [`OVERVIEW.md`](OVERVIEW.md) | **why** — read before the lab |
| [`README.md`](README.md) | **the brief** — targets, deliverables, rubric |
| [`CONCEPTS.md`](CONCEPTS.md) | **the reference** — concept → code → theory. Keep it open |
| this file | **the actions** — follow it during the lab |

**Keep a scratch file open from the start.** Many steps say *write this down*.
Those notes are your report.

**This lab is in pairs.** Decide now who drives first, and swap at each part.
The person not typing reads the numbers out and challenges them.

---

## The lab in one line

> Agents currently Ctrl-F a PDF and it fails, because they type *"how long do I
> have to file"* and the document says *"within 30 days of discharge"*. Build
> the search layer that Labs 4–7 sit on.

---

## Before you sit down

- [ ] `make setup-full` — **Lab 3 needs the retrieval stack.** ~1.8 GB, mostly
      PyTorch. **Do this the night before, not in the room.**
- [ ] `make check` → no `warn` lines left about `chromadb`, `rank_bm25`,
      `sentence_transformers`
- [ ] `OVERVIEW.md` read
- [ ] T4 notes skimmed — §2 (chunking), §4 (retrieval), §5 (failure modes)

> ⚠️ **The one that will bite you.** Labs 1 and 2 ran on a 290 MB install.
> Lab 3 is the first lab that needs the full one. If you arrive without it you
> will spend the first forty minutes downloading PyTorch.

---

# 0 · Setup — 15 min

**Why.** You cannot claim an improvement without a baseline you wrote down.

**0.1** Build the index and run the provided baseline:

```bash
python labs/lab3/search.py --baseline
```

First run takes 1–3 minutes (embedding the corpus). Instant afterwards — the
cache is content-addressed.

**0.2 — Write the baseline numbers down before you change anything.**
nDCG@10, recall@5, hit_rate@1, MRR. All four.

**0.3** Note what you are working with: **30 documents**, of which **16** are
real Aurora policies and **14 are distractors** — motor claims, travel
exclusions, a life-insurance grace period. They compete *lexically* with the
real answers. A corpus without distractors makes every method look equally good.

> **Done when:** four baseline numbers are in your notes.

> 📌 **n = 42, not 45.** Three questions (Q36, Q38, Q39) have **no** relevant
> document, so recall is undefined for them. Exclude them from retrieval metrics
> and **say so in your report.**

---

# 1 · Part A — chunking — 40 min

**Why.** This is the **biggest single lever in the whole lab**, and it is
upstream of everything else. A chunk that splits an answer in half cannot be
retrieved by any retriever, however good.

**1.1 — `A1`. Sweep all four strategies at 800 characters.**

```bash
python labs/lab3/search.py --sweep chunking
```

Report nDCG@10, recall@5, hit_rate@1, MRR, **chunk count**, and index build cost
for each of fixed · sliding · recursive · markdown-aware.

> 💡 **Theory.** T4 §2.3 — the four strategies.

**1.2 — `A2`. Take the winner, sweep size ∈ {400, 800, 1600}.**

**The relationship is not monotonic.** Explain the shape with the dilution
argument: a bigger chunk contains the answer *and* more unrelated text, so the
single vector representing it drifts away from any specific question.

> 💡 **Theory.** T4 §2.2.

**1.3 — `A3`. The heading-path prefix.** Run markdown-aware **with and without**
it. Report the delta.

> Watch for something odd: the prefix can *lower* `hit_rate@5` while raising
> `hit_rate@1` and nDCG. That is not a contradiction — **it improves ranking,
> not recall.** If you see it, say so; it is a good observation.

**1.4 — `A4`. Find one question where chunking is clearly the culprit.** Print
the chunk that *should* have matched and the chunks that did. This is **failure
mode 2** from T4 §5, in the flesh. Put it in the report.

> **Checkpoint.** Markdown-aware at 800 should beat fixed at 800 by a clear
> margin. **If all four are within a point of each other, your chunker is not
> actually being applied** — the usual cause is rebuilding the retriever while
> silently reading a cached index.

---

# 2 · Part B — dense vs BM25 vs hybrid — 40 min

**Why.** The headline question of the lab, and the one where the lecture's
general advice and your corpus will disagree.

**2.1 — `B1`.** Run all three on your best chunking.

```bash
python labs/lab3/search.py --sweep retrieval
```

**2.2 — `B2`. This is the important part.** Break the results down **by question
kind** — and **use MRR**.

> ⚠️ **The trap is armed by default.** `kind_table()` defaults to
> `hit_rate@5`, on which every retriever here scores 0.93–0.98. **You will see
> nothing.** Pass a metric with headroom.
>
> How badly it hides things: on `hit_rate@5` dense vs BM25 is 0.976 vs 0.929 —
> "no interesting difference". On **MRR** the same comparison is **0.872 vs
> 0.693.** A saturated metric does not report "no difference"; it reports
> **nothing at all**, and the two look identical.

**2.3** Two questions in particular. Report per-question MRR for each retriever:

| | what it is | why it matters |
|---|---|---|
| **Q44** | `AUR-HI-SIL-2026`, an exact identifier | dense has no reason to place these tokens near anything |
| **Q41** | *"if I skip paying on time…"* | zero lexical overlap with "grace period" |

Then look at what **hybrid** does to each. Explain the mechanism in two
sentences.

**2.4 — `B3`.** Tune RRF's `k` over {10, 30, 60, 100}. The effect should be
**small — and that is the point.** Insensitivity to `k` is exactly why RRF is a
good default.

**2.5 — `B4`.** Try unequal fusion weights. Does anything beat 1:1? **Be honest
about whether the difference exceeds noise at n = 42.**

**2.6 — `B5`. The finding you must not suppress.**

On this corpus, dense nDCG@10 **0.846** and hybrid **0.830**. **Hybrid is
worse.** The mechanism is in your per-kind table: dense beats BM25 on 14 of the
18 questions where they differ, so fusing in a much weaker retriever drags down
more good rankings than it rescues.

> T4 §4.3 calls hybrid *"the strongest single change most RAG systems can
> make."* That is true of the corpora it was measured on and **false here** —
> our embedding model is strong enough to handle the exact identifiers BM25
> usually rescues.
>
> **A technique that is right on average can be wrong on your data. That is why
> you measure.** If your numbers say hybrid loses, report that it loses.

---

# 3 · Part C — reranking — 35 min

**Why.** Retrieve wide, then spend real compute re-ordering a shortlist. It is
the standard second stage — and here it will teach you that "standard" is not
"always right".

**3.1 — `C1`.** Retrieve k=30, rerank to 5 with the **cross-encoder**. Report
the delta in nDCG@5, hit_rate@1, recall@5, and the added p95 latency.

> A reranker is a **model**. Models have training distributions. This one was
> trained on web search; your corpus is insurance-policy prose. Do not assume it
> transfers — measure it.

**3.2 — `C2`.** Same with the **LLM reranker**. Report quality, latency **and
cost**. This is the first configuration in the module that costs money *per
query*, and that changes the conversation.

**3.3 — `C3`. The decision.**

| Config | nDCG@5 | hit_rate@1 | p95 ms | $/1k queries |
|---|---|---|---|---|

Then state what you would deploy for **(a)** an interactive agent-facing search
box and **(b)** an overnight batch job.

> **They should not be the same answer.** If they are, explain why. Same
> quality numbers, different latency budget, different decision — that is the
> whole point of measuring the triple.

**3.4 — `C4`.** Find a query where reranking made things **worse**. There will
be one. Diagnose it — **failure mode 5** from T4 §5.

---

# 4 · Part D — index and metadata — 25 min

**Why.** Two lessons: an approximation you adopt too early costs you, and the
best retrieval fix is often not a retrieval change at all.

**4.1 — `D1`.** Move to Chroma (HNSW), re-run your best configuration, report
the quality gap against exact search. **Confirm the number rather than assuming
it.**

**4.2 — `D2`. Scale it up**, because at ~160 chunks the comparison is
meaningless:

```bash
python scripts/expand_corpus.py --docs 4000     # ~40k filler chunks
```

Ballast only — no golden answers — so index it but **exclude it from quality
reporting**.

Time a query on exact NumPy vs HNSW at **~160, ~4k and ~40k chunks**. Report the
three timings, **identify the crossover**, and explain it.

> At the smallest scale **HNSW is slower.** Per-query graph traversal and Python
> call overhead lose to a single BLAS matmul over 164 vectors. ANN is an
> approximation you adopt when exact search stops fitting — not before.

**4.3 — `D3`. The trap.** Q29, Q30, Q31 each have a correct answer in
`claims-timelines` and a **wrong** one in `claims-timelines-2024-ARCHIVED`.

Add `status` metadata at ingest (`current` / `archived`) and filter at query
time. Report hit_rate@1 on those three **before and after**.

Then answer the question that matters:

> **This fix required no change to the retriever at all.** What does that tell
> you about where to look first when retrieval quality is poor?

> 💡 **Theory.** T4 §2.4 — *the best retrieval fix is often not retrieval.*

---

# 5 · Show & tell — 4 minutes per pair

1. Your final configuration and its numbers — 1 min
2. Your per-kind table, and what it showed that the aggregate hid — 1 min
3. **The one result that surprised you** — 1 min
4. Questions — 1 min

---

## Deliverables checklist

- [ ] `labs/lab3/search.py` — your completed sweeps
- [ ] `reports/lab3_sweeps.json`
- [ ] `report.md`, at most three pages:
  - [ ] chunking table + the size curve, with the dilution explanation
  - [ ] retrieval table **broken down by question kind**, with the Q44/Q41 analysis
  - [ ] reranking decision table + **two different deployment answers**
  - [ ] metadata-filter before/after on Q29–Q31
  - [ ] final recommended configuration with all its numbers
  - [ ] **one thing that surprised you**
- [ ] You stated that you excluded Q36/Q38/Q39 and why
- [ ] You stated what the greedy one-axis-at-a-time sweep could miss

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| `ModuleNotFoundError: chromadb` / `sentence_transformers` | You are on the Lab 1–2 install. Run `make setup-full`. |
| All four chunkers score the same | The chunker is not being applied — you are reading a cached index. |
| The per-kind table shows nothing | You are on `hit_rate@5`. It is saturated. Use MRR. |
| First run is very slow | Embedding the corpus. Once only; it is cached afterwards. |
| The LLM reranker takes forever | It makes 30 **sequential** calls. Parallelising is the obvious fix. |
| `recall` is `nan` for some question | Q36/Q38/Q39 have no relevant document. Exclude them. |

**Stuck for more than ten minutes? Ask.**

---

## The sentence to leave with

> ### A technique that is right on average can be wrong on your data.
