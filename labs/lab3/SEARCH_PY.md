# `labs/lab3/search.py` — what is written for you, and what is yours

Lab 3 is one file. This page documents it so you are not reverse-engineering
scaffolding when you should be running sweeps.

**The contract:** everything above the `sweeps (yours)` banner is provided and
correct — corpus loading, metric computation, table printing. Everything below
it is four functions that `raise NotImplementedError`. You write those four.

You should not need to modify anything above the banner, and you **must not**
modify `aip/chunking.py` or `aip/retrieval.py` — Labs 4–7 depend on them.

---

## Running it

```bash
python labs/lab3/search.py --baseline          # provided, works today
python labs/lab3/search.py --sweep chunking    # Part A  -- yours
python labs/lab3/search.py --sweep retrieval   # Part B  -- yours
python labs/lab3/search.py --sweep rerank      # Part C  -- yours
python labs/lab3/search.py --sweep index       # Part D  -- yours
```

---

## Part 1 — the scaffolding (provided)

### `load_corpus() -> dict[str, str]`
Reads `data/corpus/*.md`. Returns `{doc_id: text}`, 30 documents. The `doc_id`
is the filename stem — you will need that in Part D to spot `ARCHIVED`.

### `load_questions(include_unanswerable=False) -> list[dict]`
Reads the 45-question golden set and **drops the three with no relevant
document** (Q36, Q38, Q39), leaving **n = 42**.

> Do not confuse those three with the **five** questions of kind
> `unanswerable` (Q36–Q40). Two of the five keep relevant documents, because
> part of what they ask *is* supported. All five are measured properly in
> Lab 4, as refusal precision and recall.

Each row has: `id`, `question`, `relevant_docs` (list of doc ids), `kind`.

### `build_chunks(corpus, strategy="sliding", size=800, **kw) -> list[Chunk]`
Applies one of the four strategies to every document. `**kw` passes through to
the chunker (e.g. `overlap=150`), and is silently dropped if that chunker does
not accept it — so `build_chunks(corpus, "fixed", 800, overlap=150)` works and
simply ignores the overlap.

### `evaluate(retriever, questions, k=10, reranker=None, final_k=5) -> dict`
The workhorse. Runs every question, times it, and returns one dict.

Two details worth knowing:

- **Scoring is at document level.** A document counts as retrieved at rank *r*
  if *any* of its chunks does. Duplicate documents are collapsed, keeping the
  best rank.
- **Reranking is applied inside**, if you pass a `reranker` — retrieve `k`,
  rerank down to `final_k`.

What comes back:

| Key | What it is |
|---|---|
| `hit_rate@{1,3,5,10}` | did any relevant doc appear in the top k |
| `recall@{1,3,5,10}` | fraction of all relevant docs in the top k |
| `precision@{...}`, `ndcg@{...}` | as usual |
| `mrr` | 1 / rank of the first relevant doc |
| `latency_p50_ms`, `latency_p95_ms` | per-query, measured |
| `_by_kind` | every metric above, split by question kind |
| `_kind_n` | how many questions in each kind |
| `_per_question` | **hit_rate@5** per question id — ⚠️ saturated |
| `_per_question_mrr` | **MRR** per question id — use this one |

### `table(rows, cols=...) -> str`
`rows` is `{config_name: metrics_dict}`. Pass `cols` to choose columns.

### `kind_table(metrics, col="hit_rate@5") -> str`
The per-kind breakdown. **The default column is deliberately the saturated
one.** Pass `col="mrr"` or `col="ndcg@10"` in Part B, or you will see a flat
table and conclude, wrongly, that nothing differs.

### `sweep_baseline()` — provided, and your reference point
Sliding-800 dense. Run it first and **write the four numbers down.**

---

## Part 2 — the API you will call

### Chunking — `aip.chunking`

```python
STRATEGIES = {"fixed": ..., "sliding": ..., "recursive": ..., "markdown": ...}
```

| Strategy | Signature extras |
|---|---|
| `fixed_chunks(text, doc_id, size=800)` | — |
| `sliding_chunks(text, doc_id, size=800, overlap=150)` | `overlap` |
| `recursive_chunks(text, doc_id, size=800, overlap=100)` | `overlap` |
| `markdown_chunks(text, doc_id, size=1200)` | prepends `[heading > path]` |

A `Chunk` has `.text`, `.doc_id`, `.meta` (a dict — you will write to it in D3).

### Retrieval — `aip.retrieval`

```python
DenseRetriever(chunks, model=None, show_progress=True)
Bm25Retriever(chunks)
HybridRetriever(retrievers, rrf_k=60, weights=None)
ChromaRetriever(chunks=None, *, path=".chroma", collection="corpus", reset=False)
```

All expose `.search(query, k=8) -> list[Hit]`. `ChromaRetriever.search` takes an
extra `where=None` for metadata filtering.

A `Hit` has `.chunk`, `.score`, `.source`, `.rank`, plus `.doc_id` and `.text`.

### Reranking — `aip.retrieval`

```python
CrossEncoderReranker(model="cross-encoder/ms-marco-MiniLM-L-6-v2")
LLMReranker(tier="SMALL")
```

Both expose `.rerank(query, hits, k=5) -> list[Hit]`.

---

## Part 3 — the four TODOs, itemised

### `sweep_chunking()` — Part A, 40 min

| # | What to do | Why it is there |
|---|---|---|
| **A1** | All four strategies at `size=800`. Report nDCG@10, recall@5, hit_rate@1, MRR, **chunk count** and **index build time** | Chunking is the biggest single lever in the lab, and it is upstream of every other choice |
| **A2** | Take the winner, sweep `size` ∈ {400, 800, 1600} | The curve is **not monotonic**. Explain the shape with the dilution argument (T4 §2.2) |
| **A3** | Markdown **with and without** the `[heading > path]` prefix. Strip it with a list comprehension over the chunks — **do not edit `aip/chunking.py`** | Isolates one trick and measures it. Watch for it *lowering* hit_rate@5 while raising hit_rate@1 — ranking and recall are different things |
| **A4** | Find one question where chunking is clearly the culprit. Print the chunk that should have matched, and the ones that did | Failure mode 2 from T4 §5, in the flesh |

> **Checkpoint.** Markdown at 800 should beat fixed at 800 clearly. If all four
> land within a point of each other, your chunker is not being applied — print
> the chunk count to confirm.

### `sweep_retrieval()` — Part B, 40 min

| # | What to do | Why it is there |
|---|---|---|
| **B1** | dense / bm25 / hybrid on your best chunking | The headline comparison |
| **B2** | `kind_table(m, col="mrr")` for each, then pull **Q44** and **Q41** from `metrics["_per_question_mrr"]` | ⚠️ **Use MRR.** On hit_rate@5 every retriever scores 0.93–0.98 and you will see nothing. Q44 is an exact identifier; Q41 has zero lexical overlap. They fail in opposite directions |
| **B3** | `HybridRetriever(..., rrf_k=k)` for k ∈ {10, 30, 60, 100} | The effect should be **small — and that is the point.** Insensitivity is why RRF is a good default |
| **B4** | `HybridRetriever(..., weights=[2.0, 1.0])` and similar | Does anything beat 1:1? Be honest about whether it exceeds noise at n = 42 |
| **B5** | Report the hybrid result **whichever way it lands** | On this corpus hybrid is *worse* than dense. If your numbers say so, say so |

### `sweep_rerank()` — Part C, 35 min

Retrieve wide, rerank narrow: `evaluate(r, questions, k=30, reranker=rr, final_k=5)`.

| # | What to do | Why it is there |
|---|---|---|
| **C1** | `CrossEncoderReranker`. Report Δ nDCG@5, hit_rate@1, recall@5 and **added p95** | First run downloads ~90 MB. A reranker is a model with a training distribution — this one learned web search |
| **C2** | `LLMReranker`. Report quality, latency **and cost** | First configuration in the module that costs money *per query*. That changes the conversation |
| **C3** | The decision table, then **two different deployment answers** — interactive search box vs overnight batch | They should not match. Same numbers, different latency budget, different call |
| **C4** | Find a query reranking made **worse**, using `_per_question_mrr` before and after | Failure mode 5 from T4 §5 |

### `sweep_index()` — Part D, 25 min

| # | What to do | Why it is there |
|---|---|---|
| **D1** | `ChromaRetriever` vs `DenseRetriever` on your best config. Report the quality gap | Confirm the number rather than assuming it |
| **D2** | `python scripts/expand_corpus.py --docs 4000`, then time both at ~160, ~4k and ~40k chunks | At small scale HNSW is **slower**. Find the crossover and explain it. Index the ballast; exclude it from quality reporting |
| **D3** | Set `chunk.meta["status"] = "archived" if "ARCHIVED" in doc_id else "current"`, then `ChromaRetriever.search(..., where={"status": "current"})`. Report **hit_rate@1** on Q29/Q30/Q31 before and after | The fix needs **no retriever change at all.** That is the lesson |

---

## The three traps built into the scaffolding

They are deliberate. Knowing they exist does not spare you from thinking.

1. **`kind_table()` defaults to `hit_rate@5`**, which is saturated. So does
   `metrics["_per_question"]`. Use `col="mrr"` and `_per_question_mrr`.
2. **`build_chunks` silently swallows unsupported kwargs.** Handy, but it means
   a typo'd parameter fails quietly. Check the chunk count changed.
3. **Everything is cached.** Re-running is nearly free — which is good, and also
   why a stale index can convince you your new chunker "made no difference".

## Common errors

| Symptom | Cause |
|---|---|
| `NotImplementedError` | The sweep you asked for is one of the four you write |
| `ModuleNotFoundError: chromadb` | You are on the Labs 1–2 install. `make setup-full` |
| All four chunkers score identically | Chunker not applied — print the chunk count |
| The per-kind table is flat | `hit_rate@5`. Saturated. Use MRR |
| `recall` is `nan` | Q36/Q38/Q39 — already excluded by `load_questions()` |
| First run very slow | Embedding 30 documents. Once, then cached |
| LLM reranker takes ~28 s/query | 30 sequential calls. Parallelising is a legitimate fix to report |
