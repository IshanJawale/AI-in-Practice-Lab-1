# Lab 3 — Concepts
### Keep this open while you work

| Concept | In the code | In the theory |
|---|---|---|
| Chunking strategies | `aip/chunking.py` | T4 §2.3 |
| The dilution trade-off | your size sweep | T4 §2.2 |
| Heading-path prefix | `markdown_chunks` | T4 §2.4 |
| Embeddings and cosine | `aip/embed.py` | T4 §1.1 |
| Dense retrieval | `DenseRetriever` | T4 §4.1 |
| BM25 and IDF | `Bm25Retriever` | T4 §4.2 |
| Hybrid / RRF | `HybridRetriever` | T4 §4.3 |
| Two-stage reranking | `CrossEncoderReranker`, `LLMReranker` | T4 §4.4 |
| Retrieval metrics | `aip/evals.py::retrieval_metrics` | T3 §3.3, T4 |
| Metric saturation | your Part B | T4 (the lab's own trap) |
| ANN / HNSW | `ChromaRetriever` | T4 §3.2 |
| Metadata filtering | your D3 | T4 §2.4 |
| Greedy sweeps | your procedure | — |

---

## Chunking, and the dilution trade-off

**What it is.** Documents are split before embedding, because one vector cannot
represent a whole document usefully. Four strategies, in `aip/chunking.py`:

| Strategy | Splits on | Cost of it |
|---|---|---|
| `fixed_chunks` | character count | Cuts mid-sentence, mid-rule |
| `sliding_chunks` | character count, with overlap | Duplication; the answer appears twice |
| `recursive_chunks` | paragraph → sentence → character | Respects prose structure |
| `markdown_chunks` | headings, **and prepends the heading path** | Needs real markdown |

**The dilution argument (T4 §2.2).** A chunk embedding is one point standing in
for everything in the chunk. Pack three unrelated rules into it and the vector
sits *between* them — close to none of them. That is why 1600 is worse than 800.

**Why it is not monotonic.** Go small enough and a chunk no longer contains a
complete rule, so the answer splits across chunks and recall falls. The curve
has a knee, and on this corpus it is near 400. You sweep because the knee moves
with the corpus.

**The heading-path prefix** is the cheapest win in the lab: it tells the
embedding what section the text belongs to. Measured in isolation: **+0.054
nDCG@10, +0.143 hit_rate@1** — and it *lowers* `hit_rate@5`. It improves
**ranking**, not **recall**. Report both halves.

---

## Dense retrieval, BM25, and their blind spots

**Dense.** Embed the query, embed every chunk, rank by cosine similarity. It
matches on **meaning**, so it handles paraphrase — *"if I skip paying on time"*
against *"grace period"*, which share no words at all.

**BM25.** A lexical score built on term frequency and **inverse document
frequency** — a term appearing in few documents is worth more. It matches on
**words**, so a rare exact token like `AUR-HI-SIL-2026` scores enormously in the
one document containing it. An embedding has to represent that string as a point
in a space learned from meaning, where one unfamiliar identifier looks much like
another.

**In the code.** `DenseRetriever`, `Bm25Retriever` in `aip/retrieval.py`.

**In the theory.** T4 §4.1–4.2.

**The two questions that isolate this.** Q44 (identifier): dense 0.50, BM25
1.00. Q41 (paraphrase): dense 1.00, BM25 0.00. They fail on *different*
questions — which is the entire argument for fusing them.

---

## Hybrid retrieval and Reciprocal Rank Fusion

**What it is.** Run both retrievers, fuse the **ranks** rather than the scores:

```
RRF(d) = Σ  1 / (k + rank_i(d))        k is a constant, conventionally 60
```

Ranks are used because the two scores are not comparable — a cosine of 0.83 and
a BM25 score of 14.2 live on different scales. `k` damps the influence of the
very top ranks so one retriever cannot dominate.

**In the code.** `HybridRetriever`.

**In the theory.** T4 §4.3 — which calls it "the strongest single change most
RAG systems can make".

**On this corpus it loses**: dense 0.846, hybrid 0.830. RRF counts a weak
retriever's opinion on **every** query, not only the ones it is good at. Dense
beats BM25 on 14 of the 18 questions where they differ, so fusion drags more
good rankings down than it rescues — visibly: it took Q44 from 0.50 to 1.00 and
Q41 from 1.00 to 0.50.

**The transferable point.** A technique that is right on average can be wrong on
your data. Published best practice is a prior, not a result.

---

## Two-stage retrieval: retrieve wide, rerank narrow

**What it is.** Retrieve 30 cheaply, then score each candidate *against the
query* with something more expensive, and keep the best 5. A bi-encoder (dense
retrieval) embeds query and document separately; a **cross-encoder** sees both
together, which is far more accurate and far too slow to run over a whole
corpus.

**In the code.** `CrossEncoderReranker` (a local model) and `LLMReranker` (one
model call per candidate).

**In the theory.** T4 §4.4.

**Measured here.** The cross-encoder **lowers** nDCG@10 (0.804 → 0.788) and
costs 131 ms — `ms-marco-MiniLM-L-6-v2` is trained on web search and is out of
domain on policy prose. The LLM reranker is the best configuration in the lab
(nDCG@10 0.860) and takes **28 seconds**, because it makes 30 calls *in series*.

**The trap.** A reranker is a model with its own training distribution.
"Reranking helps" is a claim about a match between that distribution and yours.

---

## Retrieval metrics, and saturation

**In the code.** `aip/evals.py::retrieval_metrics`.

| Metric | Asks | Use when |
|---|---|---|
| `hit_rate@k` | Is a relevant doc in the top k at all? | Sanity check |
| `recall@k` | What fraction of relevant docs are in the top k? | Sizing the generator's window |
| `MRR` | 1 / rank of the first relevant doc | Ranking quality, one answer |
| `nDCG@k` | Rank-weighted gain over the whole list | The headline; several relevant docs |

**Saturation is the trap of this lab.** Every retriever here scores 0.93–0.98 on
`hit_rate@5`. The first run of the dense-vs-BM25 comparison used it, saw 0.976
against 0.929, and concluded "no interesting difference". On MRR the same
comparison is **0.872 against 0.693**.

A saturated metric does not report "no difference" — it reports **nothing**, and
the two look identical. **Choosing a metric with headroom is part of the job.**

**In the theory.** T3 §3.3.

---

## ANN, HNSW, and measuring at the right scale

**What it is.** Exact search compares the query to every vector — one matrix
multiply, O(n). Approximate nearest neighbour indexes trade a little recall for
sublinear search. **HNSW** builds a navigable small-world graph in layers and
walks it greedily.

**In the code.** `ChromaRetriever` versus `DenseRetriever`.

**In the theory.** T4 §3.2.

**Measured here.** Identical quality, and HNSW is **3.6× slower** — 1.39 ms
against 0.39 ms. At 164 vectors there is no scale to trade against, and per-query
graph traversal in Python loses to a single BLAS matmul.

**The trap.** This is a benchmark-validity lesson, not a verdict on HNSW. A
comparison run at the wrong operating point tells you nothing about the one you
will deploy at — which is why D2 has you scale to 4k and 40k chunks and find the
crossover.

---

## Metadata filtering

**What it is.** Attach structured fields at ingest (`status: current |
archived`), then constrain the search at query time.

**In the code.** Your D3.

**In the theory.** T4 §2.4 — "other things that matter more than the embedding
model".

**Measured here.** On the three trap questions, hit@1 goes **0.667 → 1.000**. It
is free, and **it is not a retriever change at all.**

**The trap.** Deleting the archived document is the wrong fix — you may need it
for an audit, or for a claim filed under the old rules. Keep it, label it, and
let the query decide.

---

## Greedy sweeps

**What it is.** Sweeping one axis, fixing the winner, moving to the next —
instead of the full 4 × 3 × 3 × 3 × 2 = 216-cell grid.

**Not in the lectures.**

**What it assumes.** That the axes are **separable** — that the best chunker
given dense retrieval is also the best chunker given BM25. Often roughly true;
not guaranteed, and you have direct evidence in this lab that it fails, because
reranking helped one retrieval configuration and hurt another.

**What to say in your report.** That the procedure is greedy, that it can miss
interactions, and — ideally — name one pair of axes you suspect interact.
