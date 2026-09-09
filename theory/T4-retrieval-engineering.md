# T4 — Retrieval Engineering and the Seven Failure Modes of RAG
**AI in Practice I · Module 1 · Theory 4 of 4 · 90 minutes**

> **Prepares you for:** Labs 3, 4 and 5
> **Assumes from the LLM theory course:** what an embedding is, cosine similarity,
> the RAG pipeline diagram. We are going to take that diagram apart.

---

## Running order

| Min | Segment |
|---|---|
| 0–10 | §1 Why RAG, and what it is really competing with |
| 10–25 | §2 Ingestion and chunking — where most of the quality is decided |
| 25–45 | §3 Indexing: exact, ANN, and what a vector database actually is |
| 45–60 | §4 Retrieval: dense, lexical, hybrid, rerank |
| 60–80 | §5 The seven failure modes, and how to tell them apart |
| 80–90 | §6 Generation, citations, refusal · Labs 3–5 briefing |

---

## 1. Why RAG

A foundation model knows what was in its training data, approximately, up to a
date. It does not know your company's policies, last week's incident, or this
customer's history. RAG supplies those at inference time.

### 1.1 The real comparison

RAG is usually presented against fine-tuning. That is the wrong comparison for
most problems, because they do different things:

| | RAG | Fine-tuning | Long context |
|---|---|---|---|
| Adds **knowledge** | yes | poorly | yes |
| Changes **behaviour/format/tone** | poorly | yes | somewhat |
| Update latency | seconds | hours–days | seconds |
| Attribution possible | **yes** | no | partially |
| Per-query cost | retrieval + moderate input | low input | very high input |
| Access control per document | **yes** | no | no |
| Corpus size ceiling | unbounded | n/a | context window |

The two rows in bold usually decide it in an enterprise. **Attribution** —
being able to say *which document* the answer came from — is a hard requirement
in insurance, finance, medicine, and law, and fine-tuning cannot provide it at
all. **Per-document access control** is likewise unachievable by baking
knowledge into weights: once it is in the model, everyone who can call the
model can reach it.

The honest comparison in 2026 is RAG versus **long context**. Windows are large
enough to hold a small corpus outright. Use long context when the corpus is
small, static, and every query genuinely needs all of it. Use RAG when the
corpus is large, changes, needs attribution, or has per-user permissions —
and note that you pay for every input token on every call, so "just put it all
in the context" is a decision with a monthly invoice attached.

They also compose: retrieve widely, then use a large window to hold 30 chunks
instead of 5.

---

## 2. Ingestion and chunking

> **The strongest claim in this lecture: for a typical corpus, chunking
> strategy affects end-to-end RAG quality more than the choice of embedding
> model, and by a wide margin. It is also the step students skip.**

### 2.1 Parsing comes first, and it is not glamorous

Before chunking there is extraction, and it is where corpora quietly break:

- **PDFs** are a layout format, not a text format. Two-column academic PDFs
  extract as interleaved nonsense with a naive parser. Scanned PDFs need OCR.
- **Tables** are the hard case. A table flattened to prose loses its
  row/column relationships, and a table split across chunks loses its header.
  Extract tables separately, keep them whole, and prepend the header to any
  fragment.
- **HTML** carries navigation, cookie banners, and footers that will pollute
  every embedding in the corpus.
- **Headers and footers** repeated on 400 pages create 400 near-identical
  chunks that crowd out real content in every retrieval.

Our corpus is clean Markdown so that Labs 3–5 can focus on retrieval. Be aware
that in a real project this step is often half the work.

### 2.2 The chunking trade-off

```
small chunks (200 tok)          large chunks (2000 tok)
├─ precise embeddings           ├─ context preserved
├─ tight, cheap context         ├─ fewer boundary splits
├─ ✗ answer split across two    ├─ ✗ diluted embedding: one topic in a
│    chunks; neither retrieves  │    chunk about five topics
└─ ✗ no surrounding context     └─ ✗ expensive, and distractor-heavy
```

The dilution point deserves emphasis, because it is the non-obvious one. An
embedding is a single vector for the whole chunk. A 2,000-token chunk covering
five topics produces a vector that is the average of five things and is close
to nothing in particular. Larger chunks are not simply "safer".

### 2.3 The four strategies you will measure in Lab 3

| Strategy | What it does | Best for |
|---|---|---|
| **Fixed** | Hard cut every N characters | Nothing. It is the baseline that shows you why the others exist |
| **Sliding** | N characters with overlap | Prose with no structure. Overlap ≈ 10–20% of size |
| **Recursive** | Split on the largest natural boundary that fits (paragraph → line → sentence → word) | Good general default |
| **Markdown-aware** | Split on headings; **prepend the heading path** to each chunk | Structured documents — which is most enterprise content |

The heading-path trick in the last row is small and unreasonably effective. A
chunk that reads

```
[Claims > Reimbursement > Submission] Submit the claim within 30 days of discharge.
```

embeds far closer to *"how long do I have to file a claim?"* than the same
sentence alone, because the sentence alone contains neither "claim submission"
as a topic nor any signal about which process it belongs to. Cheap, and worth
several points of hit_rate.

### 2.4 Other things that matter more than the embedding model

- **Contextual retrieval.** Prepend a one-sentence, LLM-generated description of
  where the chunk sits in the document. Costs one small-model call per chunk at
  ingest — once — and reliably beats every other single change. Anthropic
  reported ~35% reduction in retrieval failure from this plus BM25.
- **Metadata.** Store `plan`, `effective_date`, `status` alongside each chunk
  and filter before searching. A metadata filter that excludes archived
  documents solves our `claims-timelines-2024-ARCHIVED` trap completely, and it
  costs nothing at query time. **The best retrieval fix is often not retrieval.**
- **Deduplication.** Near-duplicate chunks waste the top-k slots.
- **Small-to-big.** Embed a small precise chunk; return the larger parent
  section it belongs to. Best of both, at the cost of some bookkeeping.

---

## 3. Indexing

### 3.1 What a "vector database" actually is

Four things bundled together, and it is worth knowing which one you need:

1. **A vector index** for approximate nearest-neighbour search.
2. **A metadata store**, so you can filter by `plan == "gold"`.
3. **Persistence and CRUD**, so you can update a document without a rebuild.
4. **Operational features** — sharding, replication, auth, backups.

At a few hundred chunks — Lab 3's real scale — you need none of them. A NumPy array and an
`argsort` is exact, sub-millisecond, and has no failure modes. **Exact search is
the right answer up to roughly 100k vectors on a laptop**, and starting there
removes ANN recall as a confounder while you are learning.

You need a real vector database when you have millions of vectors, concurrent
writes, or per-document access control. Chroma (embedded, no server) is what we
use from Lab 4 for persistence; pgvector, Qdrant, Weaviate, Milvus and the
managed services differ mainly on operations, not on retrieval quality.

### 3.2 ANN: the one algorithm to understand

**HNSW** (Hierarchical Navigable Small World) is the default in essentially
every vector store. The intuition: build a layered graph where the top layer
has long-range links and lower layers are progressively denser. Search greedily
from the top — take big jumps to the right neighbourhood, then refine. Query is
O(log n) rather than O(n).

Three parameters, and they trade the same way in every implementation:

| Parameter | Raises | Costs |
|---|---|---|
| `M` (links per node) | recall | memory, build time |
| `ef_construction` | index quality | build time |
| `ef_search` | recall at query time | query latency |

**ANN is approximate. It will miss results that exact search finds.** Typical
recall at default settings is 95–99%, which is usually fine — but when you
switch from exact to ANN and your nDCG drops two points, that is the reason,
and Lab 3 asks you to measure exactly this so it is never a mystery later.

---

## 4. Retrieval

### 4.1 Dense retrieval and its blind spot

Embed the query, embed the chunks, return the nearest. Its strength is semantic
matching: *"how long do I have to file?"* finds *"Claims must be submitted
within 30 days of discharge"* with no shared vocabulary.

Its blind spot is the mirror image. Dense retrieval is systematically weak on:

- **exact identifiers** — `AUR-HI-SIL-2026`, order numbers, error codes
- **rare proper nouns** not well represented in the embedding model's training
- **numbers and dates** — `7.5 dioptres` and `4.5 dioptres` embed almost identically
- **negation** — "not covered" and "covered" are near-neighbours in embedding space

These are not corner cases. They are a large fraction of what people type into
an enterprise search box.

### 4.2 BM25, and why the old thing is still here

BM25 scores by term frequency, inverse document frequency, and a length
normalisation. It is fifty years old in lineage, it has no learned parameters,
it is essentially free to run — and it beats dense retrieval on every one of
the four blind spots above, because it matches the literal string.

> **Always include BM25 as a baseline. If your fancy dense pipeline cannot beat
> BM25 on your corpus, that is a finding, and it happens more often than the
> vector-database marketing suggests.**

### 4.3 Hybrid: Reciprocal Rank Fusion

Combining them requires care, because BM25 scores (unbounded, corpus-dependent)
and cosine similarities (−1 to 1) are not on a comparable scale. Every attempt
to min-max normalise them is fragile across queries.

RRF sidesteps the problem by fusing **ranks**, which are comparable by
construction:

```
score(d) = Σ_r  1 / (k + rank_r(d))          k ≈ 60
```

A document ranked 1st by BM25 and 40th by dense scores 1/61 + 1/100. One ranked
3rd by both scores 2/63. Documents that both retrievers like rise; documents
only one likes still get a chance. `k = 60` damps the difference between rank 1
and rank 2 so a single retriever cannot dominate.

Hybrid is, on average, the strongest single change most RAG systems can make,
and it is about fifteen lines. See `aip/retrieval.py::HybridRetriever`.

**But "on average" is doing real work in that sentence.** Fusion helps when the
two retrievers have complementary strengths *and comparable overall quality*.
Fuse a strong retriever with a much weaker one and you drag good rankings down
more often than you rescue bad ones. On our own Lab 3 corpus, dense scores
nDCG@10 0.846 and hybrid 0.830 — hybrid **loses**, because a modern embedding
model already handles the exact identifiers BM25 classically rescues. Lab 3
asks you to measure this rather than assume it, and to report whichever way it
lands.

### 4.4 Two-stage retrieval: retrieve wide, rerank narrow

```
   query ──▶ hybrid retrieve k=30 ──▶ rerank ──▶ top 5 ──▶ generator
             (cheap, high recall)     (expensive,  (precise,
                                       accurate)    small context)
```

A **bi-encoder** (ordinary embeddings) encodes query and document separately,
which is what makes precomputation possible — and also means it never sees
them together. A **cross-encoder** reads the pair jointly and can judge
relevance in a way a bi-encoder structurally cannot. It is far too slow for the
whole corpus, and exactly right for 30 candidates.

Typical: +5 to +15 points of nDCG@5, at +50–200 ms. Whether that is worth it is
a measurement, not an opinion, and Lab 3 makes you take it.

### 4.5 Query-side transforms

The query and the documents are written by different people for different
purposes, and often share little vocabulary. Three fixes:

- **HyDE** — ask the model to *write the passage that would answer the
  question*, then embed that. Questions and answers live in different regions
  of embedding space; a hypothetical answer lands in the right one.
  (`aip.rag.hyde`)
- **Multi-query** — generate 3 paraphrases, retrieve for each, fuse with RRF.
  Buys recall when phrasing is unpredictable.
- **Decomposition** — split a multi-part question into parts, retrieve for each.
  Required for genuine multi-hop questions like Q20 in our golden set.

All three cost an extra small-model call per query. Measure whether they earn it.

---

## 5. The seven failure modes

When a RAG system gives a wrong answer, *"RAG is bad"* is not a diagnosis.
Exactly one stage usually failed. This table is the diagnostic procedure, and
Lab 5 is built entirely around it.

| # | Stage | Symptom | How to confirm | Fix |
|---|---|---|---|---|
| 1 | **Missing content** | Answer is simply not in the corpus | grep the corpus | Fix the data. No retrieval change can help |
| 2 | **Chunk boundary** | Answer straddles two chunks; neither is retrievable alone | Print the chunks around the gold answer | Larger chunks, overlap, markdown-aware, small-to-big |
| 3 | **Embedding mismatch** | Right chunk exists, ranks below 30 | Search for the gold chunk's text verbatim — if that retrieves it, the query is the problem | Hybrid, HyDE, contextual retrieval |
| 4 | **Ranking** | Right chunk is in the top 30 but not the top 5 | Compare hit_rate@30 with hit_rate@5 | Rerank; raise final k |
| 5 | **Reranker error** | Right chunk was in the pool and the reranker dropped it | Log pre- and post-rerank ids | Different reranker; keep top-1 from stage 1 unconditionally |
| 6 | **Generation** | Right chunk was in the context and the answer is still wrong | **Run the generator on gold context.** Still wrong ⇒ generation | Prompt, model tier, fewer distractors |
| 7 | **Presentation** | Answer correct, citation wrong or missing | `aip.guards.enforce_citations` | Output contract; validate before returning |

**The single most useful experiment in RAG debugging is #6: run generation with
gold context.** It splits the problem cleanly in two and takes ten minutes to
set up. Do it before anything else.

Diagnostic tree:

```
                    wrong answer
                         │
        ┌────────────────┴────────────────┐
   is the answer in the corpus at all?
        │ no                              │ yes
        ▼                                 ▼
   FAILURE 1                    does gold context fix it?
   (data problem)                        │
                          ┌──────────────┴──────────────┐
                       yes │                            │ no
                           ▼                            ▼
                  retrieval problem                 FAILURE 6
                           │                       (generation)
              ┌────────────┴────────────┐
       is it in the top 30?
              │ no                      │ yes
              ▼                         ▼
       FAILURE 2 or 3            FAILURE 4 or 5
   (chunking / embedding)          (ranking)
```

---

## 6. Generation, citation, refusal

Retrieval is most of the work but the last stage has its own contract.

### 6.1 Three non-negotiable rules in the answer prompt

1. **Answer only from the sources.** Explicitly forbid falling back on general
   knowledge. Without this, the model happily blends training data with
   retrieved content and you cannot tell which is which.
2. **Cite by index.** Number the sources; require `[1]`-style citations. Then
   *validate the indices in code*. A citation to `[7]` when you supplied five
   sources is a detectable hallucination — and it costs nothing to check.
   (`aip.guards.enforce_citations`)
3. **Give an explicit refusal string.** *"I don't have enough information in the
   provided sources to answer that."* A model with no legal way to fail will
   invent an answer. Refusal must be a first-class, exactly-specified output.

### 6.2 The refusal trade-off

Refusal is a precision/recall dial, and where you set it is a product decision,
not a technical one:

- Refuse too readily → useless assistant, users go around it.
- Refuse too rarely → confident wrong answers, which in insurance or medicine is
  worse than no answer at all.

Measure both directions on your golden set: **refusal recall** (of the
unanswerable questions, how many were refused?) and **refusal precision** (of
the refusals, how many were genuinely unanswerable?). Reporting only one is how
you ship a system that refuses everything and scores beautifully.

### 6.3 Contradictions

Real corpora contradict themselves. Ours does, deliberately: `claims-timelines`
says 45 days for a query response, and `claims-timelines-2024-ARCHIVED` says 30.

Three defences, in ascending order of quality:
1. Tell the generator to surface disagreement rather than pick silently.
2. Add `status` and `effective_date` metadata and filter archived documents out
   at query time.
3. Do not ingest superseded documents into the live index at all.

Note that 2 and 3 are data-layer fixes, and they are strictly better than 1.
This is the general lesson of the lecture: **most retrieval problems are solved
before the query is ever issued.**

---

## 7. Labs 3–5 briefing

- **Lab 3 — Semantic Search That Actually Works.** Build the retriever. Measure
  4 chunking strategies × 3 retrieval methods × rerank on/off against the
  45-question golden set. Report nDCG@10, recall@5, hit_rate@1, MRR, cost, p95
  latency. Note that hit_rate@5 is already ~0.93 for plain BM25 on this corpus
  and therefore useless as a headline — choosing a metric with headroom is part
  of the exercise.
  Recommend a configuration and justify it.
- **Lab 4 — RAG v1.** Add generation with enforced citations and a refusal
  contract. Get end-to-end correctness measured, including on the 5 unanswerable
  questions.
- **Lab 5 — RAG v2.** Diagnose. Classify every failure into one of the seven
  modes, fix the largest cluster, and prove the improvement with a before/after
  table on the test split.

---

## Reading

- Gao et al. (2023), *Retrieval-Augmented Generation for Large Language Models:
  A Survey* — arxiv.org/abs/2312.10997. §3–4.
- Anthropic, *Introducing Contextual Retrieval* —
  anthropic.com/news/contextual-retrieval
- Cormack et al. (2009), *Reciprocal Rank Fusion Outperforms Condorcet and
  Individual Rank Learning Methods* — the RRF paper, 2 pages, read all of it.
- Malkov & Yashunin (2016), *Efficient and robust approximate nearest neighbor
  search using HNSW graphs* — arxiv.org/abs/1603.09320. Read §3 and the figures.
- Barnett et al. (2024), *Seven Failure Points When Engineering a RAG System* —
  arxiv.org/abs/2401.05856

## Check yourself

1. Your corpus is 500 pages of policy documents. Why might markdown-aware
   chunking beat sliding-window chunking by more than switching embedding
   models would?
2. A user searches `AUR-HI-SIL-2026`. Dense retrieval returns nothing useful.
   Why, and what is the cheapest fix?
3. Explain why RRF fuses ranks rather than scores. What breaks if you min-max
   normalise scores and add them?
4. hit_rate@5 is 0.62; hit_rate@30 is 0.94. Which failure mode, and what do you
   change?
5. You add a reranker and nDCG@5 goes *down*. Give two plausible explanations
   and an experiment that distinguishes them.
6. Your system correctly refuses 5 of 5 unanswerable questions and also refuses
   12 of 40 answerable ones. Compute refusal precision and recall. Is this
   system shippable for an insurance helpdesk? Argue both sides.
