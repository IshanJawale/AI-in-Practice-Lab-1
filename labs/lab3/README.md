# Lab 3 — Semantic Search That Actually Works
**3 hours · Pairs · Prepared by T4**

> **Read [`OVERVIEW.md`](OVERVIEW.md) first** — why this lab exists, how to
> approach the three hours, the hints, and the map back to the theory
> sessions. Keep [`CONCEPTS.md`](CONCEPTS.md) open while you work.
> This file is the detail.

---

## The problem

Aurora's support agents currently find policy information by using Ctrl-F on a
PDF. It does not work: they type *"how long do I have to file"* and the document
says *"submitted within 30 days of discharge"*, so Ctrl-F finds nothing.

You are building the search layer that Labs 4–7 will sit on top of.

You get: 30 documents (`data/corpus/`) and 45 labelled questions with
document-level relevance judgements (`data/eval/rag_golden.jsonl`).

16 of the documents are Aurora Health policy documents. The other 14 are
distractors: motor claim timelines, travel exclusions, a group corporate plan
comparison, a life-insurance grace period, a senior-citizen product, an app
guide. They are there because they compete lexically with the real answers, and
a corpus without distractors makes every retrieval method look equally good.

**Find the retrieval configuration that maximises nDCG@10, and justify it
against cost and latency.**

### The search space

| Axis | Levels |
|---|---|
| Chunking | fixed · sliding · recursive · markdown-aware |
| Chunk size | 400 · 800 · 1600 characters |
| Retrieval | dense · BM25 · hybrid (RRF) |
| Reranking | none · cross-encoder · LLM reranker |
| Index | exact NumPy · Chroma HNSW |

That is far too many combinations to run exhaustively in three hours, and
noticing that is part of the lab. **Do not grid-search blindly.** Sweep one axis
at a time, fix the winner, move on. Say in your report what that greedy
procedure could miss.

### Targets on the 45-question golden set

| Metric | Target | BM25 baseline | Reference solution |
|---|---|---|---|
| nDCG@10 | ≥ 0.80 | 0.701 | 0.853 |
| recall@5 | ≥ 0.85 | 0.790 | 0.903 |
| hit_rate@1 | ≥ 0.65 | 0.524 | 0.786 |
| MRR on the `paraphrase` subset | ≥ 0.75 | 0.500 | 0.900 |
| Retrieval latency p95 | ≤ 400 ms (excluding first-time embedding) | 0.3 ms | 1.0 ms |
| Cost to build the index | reported, once | $0 | $0.008 |

Both extra columns are measured, not estimated. The reference configuration is
markdown-aware chunking at 400 characters with exact dense retrieval.

**`hit_rate@5` is not the headline here, and this matters more than it sounds.**
Every retriever on this corpus scores 0.93–0.98 on it. When the reference
solution was first run, it compared dense against BM25 on `hit_rate@5`,
saw 0.976 vs 0.929, and concluded there was no interesting difference between
them. That conclusion was wrong: on MRR the same comparison is 0.872 vs 0.693,
and the per-question picture is dramatic. A saturated metric does not report
"no difference" — it reports nothing at all, and it looks identical.

Use `nDCG@10`, `recall@5`, `hit_rate@1` and `MRR`. **Choosing a metric with
headroom is part of the job.**

Note that **3 of the 45 questions have no relevant document at all** (Q36, Q38,
Q39). **Exclude those three from retrieval metrics** — you cannot compute recall
against an empty relevant set — which leaves **n = 42**. Say in your report that
you excluded them and why.

Five questions in total are of kind `unanswerable`; the other two do have
relevant documents, because part of what they ask *is* supported. All five
belong to Lab 4, where refusal is measured properly.

---

## Timetable

| Time | Part | What you do |
|---|---|---|
| 0:00–0:15 | Setup | Build the index, run the provided baseline |
| 0:15–0:55 | **A** | Chunking sweep. The biggest single lever |
| 0:55–1:35 | **B** | Dense vs BM25 vs hybrid — and the per-question-type breakdown |
| 1:35–2:10 | **C** | Reranking, and whether it earns its latency |
| 2:10–2:35 | **D** | ANN vs exact; metadata filtering |
| 2:35–3:00 | Show & tell | Your configuration and the one surprising result |

---

## Setup (15 min)

```bash
python labs/lab3/search.py --baseline
```

This chunks the corpus with sliding windows, embeds it, and reports the
baseline. It takes 1–3 minutes the first time (embedding) and is instant after
that (cache).

Write down the baseline numbers before you change anything.

---

## Part A — Chunking (40 min)

```bash
python labs/lab3/search.py --sweep chunking
```

**A1.** Run all four strategies at 800 characters. Report nDCG@10, recall@5, hit_rate@1,
MRR, chunk count, and index build cost for each.

**A2.** Take the winner and sweep size ∈ {400, 800, 1600}. The relationship is
not monotonic. Explain the shape you see using the dilution argument from
T4 §2.2.

**A3.** The markdown-aware chunker prepends the heading path. Run it **with and
without** the prefix (`markdown_chunks` vs a variant that strips the `[...]`
prefix). Report the delta. This single trick is usually worth several points —
verify that on this corpus, and if it is not, say so and hypothesise why.

**A4.** Find one golden question where chunking is clearly the failure. Print
the chunk that should have matched and the chunks that did. Include this in
your report — it is failure mode 2 from T4 §5.

> **Checkpoint.** Markdown-aware at 800 should beat fixed at 800 by a clear
> margin. If all four are within a point of each other, check that your chunker
> is actually being applied — a very common bug is rebuilding the retriever
> while reading a cached index.

---

## Part B — Dense vs BM25 vs hybrid (40 min)

```bash
python labs/lab3/search.py --sweep retrieval
```

**B1.** Run all three on your best chunking. Report the overall table.

**B2. This is the important part.** Break the results down **by question kind**
(`kind` field in the golden set), **using MRR**. If you use `hit_rate@5` you
will see nothing — see the note above.

Dense and BM25 win on *different* subsets. Look at two questions in particular:

- **Q44** (`AUR-HI-SIL-2026` — an exact identifier)
- **Q41** ("if I skip paying on time, how long before I lose everything") — no
  lexical overlap with "grace period" at all

Report the per-question MRR for each retriever on both, and explain the
mechanism in two sentences.

**Then look at what hybrid does to each.** The reference solution measures
Q44 dense 0.50 / BM25 1.00 / hybrid 1.00, and Q41 dense 1.00 / BM25 0.00 /
hybrid 0.50. Fusion rescued one question and damaged the other. Whether that
trade is worth taking is an empirical question about your corpus, not a
principle — and on this corpus it is **not** worth taking.

**B3.** Tune RRF's `k` over {10, 30, 60, 100}. Report the effect. It should be
small — and the fact that it is small is why RRF is a good default.

**B4.** Try weighting the two retrievers unequally in the fusion. Does anything
beat 1:1? Be honest about whether the difference exceeds noise at n=42.

**B5 — the finding you are most likely to reach, and must not suppress.**
On this corpus the reference solution measures dense nDCG@10 0.846 and hybrid
0.830. **Hybrid is worse.** The mechanism is visible in the per-kind table:
dense beats BM25 on 14 of the 18 questions where they differ, so fusing in a
substantially weaker retriever drags more good rankings down than it rescues.

T4 §4.3 calls hybrid "the strongest single change most RAG systems can make."
That is true of the corpora it was measured on and false here, and the
difference is that our embedding model is strong enough to handle the exact
identifiers BM25 usually rescues. **A technique that is right on average can be
wrong on your data. This is why you measure.** If your numbers say hybrid loses,
report that it loses.

---

## Part C — Reranking (35 min)

```bash
python labs/lab3/search.py --sweep rerank
```

**C1.** Retrieve k=30, rerank to 5, with the cross-encoder. Report the delta in
nDCG@5, hit_rate@1 and recall@5, and the added p95 latency.

**C2.** Same with the LLM reranker. Report quality, latency, **and cost** — this
is the first configuration in the lab that costs money per query, and that
changes the conversation.

**C3.** The decision. Build a small table:

| Config | nDCG@5 | hit_rate@1 | p95 ms | $/1k queries |
|---|---|---|---|---|

Then state which you would deploy for (a) an interactive agent-facing search
box, and (b) an overnight batch job. **They should not be the same answer.**
If they are, explain why.

**C4.** Find a query where reranking made things *worse*. There will be one.
Diagnose it — this is failure mode 5 from T4 §5.

---

## Part D — Index and metadata (25 min)

**D1.** Move to Chroma (HNSW) and re-run your best configuration. Report the
recall gap against exact search. It should be small; confirm the number rather
than assuming it.

**D2.** The real corpus is only ~160 chunks, where exact search is
microseconds and the comparison is meaningless. Scale it up:

```bash
python scripts/expand_corpus.py --docs 4000     # ~40k filler chunks
```

Those documents are index ballast only — they contain no golden answers, so
include them in the **index** and not in your quality reporting.

Now time a query on exact NumPy vs HNSW at ~160, ~4k, and ~40k chunks. At the
smallest scale HNSW will be *slower*, because of per-query graph-traversal and
Python call overhead that a single BLAS matmul does not have. Report the three
timings, identify the crossover, and explain the mechanism.

**D3 — the trap.** Questions Q29, Q30, Q31 have a correct answer in
`claims-timelines` and a *wrong* answer in `claims-timelines-2024-ARCHIVED`.

Add `status` metadata at ingest (`current` / `archived`) and filter archived
documents at query time. Report hit_rate@1 on those three questions before and
after.

Then answer the question that matters: **this fix required no change to the
retriever at all.** What does that tell you about where to look first when
retrieval quality is poor?

---

## Deliverables

1. `labs/lab3/search.py` — your completed sweeps
2. `report.md` — at most three pages:
   - the chunking table and the size curve, with the dilution explanation
   - the retrieval table **broken down by question kind**, with the Q44/Q41 analysis
   - the reranking decision table and your two different deployment answers
   - the metadata-filter before/after on Q29–Q31
   - your final recommended configuration, with all its numbers
   - one thing that surprised you
3. `reports/lab3_sweeps.json`

---

## Rubric (9% of Module 1)

| Criterion | Weight | Full marks means |
|---|---|---|
| Retrieval quality | 20% | Meets the nDCG@10 / recall@5 / hit_rate@1 targets, including on `paraphrase` |
| Sweep discipline | 20% | One axis at a time; the greedy-search limitation acknowledged |
| Diagnostic depth | 25% | The per-kind breakdown uses a non-saturated metric and is correctly interpreted; Q44/Q41 mechanism explained; the hybrid result reported honestly whichever way it lands |
| Cost/latency reasoning | 20% | The two different deployment answers in C3 are both defended |
| Metadata insight | 15% | D3 works, and its implication is stated |

---

## Stretch

1. **Contextual retrieval** (T4 §2.4). One small-model call per chunk at ingest
   to prepend a situating sentence. Costs ~$0.02 for this corpus. Anthropic
   report ~35% fewer retrieval failures. Verify or refute on this corpus.
2. **HyDE** (`aip.rag.hyde`). Measure on the `paraphrase` subset specifically,
   where it should help most.
3. **Small-to-big.** Embed 300-character chunks, return the parent section.
4. **Query classification.** Route identifier-shaped queries to BM25 and
   natural-language queries to dense. Does routing beat fusion?
5. **Multilingual.** Translate 10 questions to Hindi and re-run. What breaks?
