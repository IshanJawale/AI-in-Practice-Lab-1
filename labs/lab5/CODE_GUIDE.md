# Lab 5 — the code: what is provided, and every TODO

One file: **`diagnose.py`**. It reads your Lab 4 output, runs the automatable
checks from the diagnostic tree, and leaves you the judgement calls.

> `aip/` is the toolkit — read it, never change it. `labs/` is your system.

---

## What you will call from `aip/`

| You need | It lives in | Signature |
|---|---|---|
| Re-run retrieval to test a hypothesis | `aip.retrieval` | `DenseRetriever`, `Bm25Retriever`, `HybridRetriever`, `ChromaRetriever` |
| Re-chunk to test a boundary fix | `aip.chunking` | `STRATEGIES`, `markdown_chunks(...)` |
| Retrieval metrics for the before/after | `aip.evals` | `retrieval_metrics(retrieved, relevant, ks=...)` |
| Re-judge after the fix | `aip.evals` | `llm_judge`, `judge_agreement` |
| The query-side fixes in the mode-3 catalogue | `aip.rag` | `hyde(question)`, `multi_query(question, n=3)` |
| Cost ceiling | `aip.cost` | `Budget(limit_usd=..., label=...)` |
| What your Lab 4 pipeline did, per query | `aip.tracing` | `read_traces()` |

**`reports/lab4.json` is the input.** Lab 4's `--full --save` writes it. Without
it this lab does not start.

---

## `diagnose.py`

### `answer_in_corpus(gold_answer, corpus, ...)` — **TODO**

Decides **mode 1**, missing content.

> The provided version is a deliberately weak substring test. **It will pass on
> a paraphrase and fail on a rewording** — so it over-reports mode 1, which
> sends you hunting for data problems that are really retrieval problems.
> Improving it is part of the lab: normalise, or check key numbers and entities
> rather than whole strings.

### `classify(row, q, corpus, ...)` — **TODO, the core of the lab**

Walk the tree from T4 §5. Branches marked TODO:

| Branch | The test | Mode |
|---|---|---|
| gold context does **not** fix it | generation was always going to fail | **6** |
| gold doc in top 30, not in final k | it was found and then buried | **4** (or **5** if a reranker dropped it) |
| gold doc **not** in top 30 | confirm by searching the gold chunk's text verbatim | **3** if that retrieves it, else **2** |

> ⚠️ **The inversion.** `gold_context_fixes_it == True` means **retrieval**
> failed, not generation. The generator was capable; it was starved. People get
> this backwards constantly, and a whole lab's diagnosis can hang on it.

**Mode 2 cannot be automated.** Mark it `needs_human_check` and go and look at
the chunks around the gold answer.

### `pareto(tally)` — provided

Ranks the clusters. Use it for A3 and again in D3 after your fix.

### Runners — provided

| Command | What it does |
|---|---|
| `--input reports/lab4.json` | classify every Lab 4 failure |
| `--pareto` | the cluster chart |
| `--save reports/lab5_diagnosis.json` | persist the tally |

---

## The fix catalogue, by mode

| Mode | Fixes, cheapest first | `aip/` to reach for |
|---|---|---|
| **1** missing content | none — say what the corpus needs | — |
| **2** chunk boundary | larger chunks · more overlap · markdown-aware · small-to-big | `aip.chunking` |
| **3** embedding mismatch | hybrid · HyDE · multi-query · contextual retrieval | `aip.retrieval.HybridRetriever`, `aip.rag.hyde`, `aip.rag.multi_query` |
| **4** ranking | raise `final_k` · cross-encoder · tune RRF weights | `aip.retrieval.CrossEncoderReranker` |
| **5** reranker | different reranker · always keep stage-1 top-1 · rerank only on a small margin | `aip.retrieval` |
| **6** generation | fewer distractors · best chunk first or last never middle · larger tier · better prompt · decompose multi-hop | `labs/lab4/rag.py` |
| **7** presentation | tighten the contract · validate and repair citations | `aip.guards.enforce_citations` |

---

## The traps

1. **Inverting the mode-6 test.** Gold context fixing it means *retrieval*.
2. **Fixing by reflex.** If your fix and your tally disagree, stop.
3. **Changing several things at once.** The number moves and you learn nothing.
4. **Only measuring what you targeted.** D2 exists because better retrieval
   routinely makes refusal precision worse.
5. **Trusting `answer_in_corpus` as shipped.** It is weak on purpose.

## Common errors

| Symptom | Cause |
|---|---|
| `FileNotFoundError: reports/lab4.json` | Lab 4's `--full --save` was never run |
| Everything classified mode 1 | `answer_in_corpus` is too literal. Improve it |
| Everything `needs_human_check` | The branches above it are still TODO |
| Cost climbs after a mode-3 fix | HyDE and multi-query add a call per query. Expected — report it |
