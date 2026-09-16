# `aip` — the shared toolkit

**AI in Practice I · Module 1: Applied GenAI**

Twelve modules, about 2,000 lines. Every lab in the module runs on this package,
and **you are expected to open it.** Nothing here is magic: each module is under
~380 lines, has no framework hiding underneath it, and is fair game to modify,
extend or replace in your own lab code.

This document is the reference. For *why* a concept matters in a given lab, see
that lab's `CONCEPTS.md`.

---

## Table of contents

- [Design rules](#design-rules)
- [How the pieces fit](#how-the-pieces-fit)
  - [The seven layers](#the-seven-layers)
  - [Dependency direction](#dependency-direction)
  - [Which module matters in which lab](#which-module-matters-in-which-lab)
  - [Reading order](#reading-order)
- [Module reference](#module-reference)
  - [`__init__.py` — the public surface](#__init__py--the-public-surface)
  - [`config.py` — model tiers and settings](#configpy--model-tiers-and-settings)
  - [`llm.py` — the model client](#llmpy--the-model-client)
  - [`cost.py` — token accounting and budgets](#costpy--token-accounting-and-budgets)
  - [`cache.py` — the content-addressed cache](#cachepy--the-content-addressed-cache)
  - [`tracing.py` — JSONL spans](#tracingpy--jsonl-spans)
  - [`chunking.py` — four chunking strategies](#chunkingpy--four-chunking-strategies)
  - [`embed.py` — embeddings](#embedpy--embeddings)
  - [`retrieval.py` — retrievers and rerankers](#retrievalpy--retrievers-and-rerankers)
  - [`rag.py` — the reference RAG pipeline](#ragpy--the-reference-rag-pipeline)
  - [`evals.py` — the evaluation harness](#evalspy--the-evaluation-harness)
  - [`guards.py` — guardrails for untrusted input](#guardspy--guardrails-for-untrusted-input)
- [Configuration and environment](#configuration-and-environment)
- [Extending or replacing a module](#extending-or-replacing-a-module)

---

## Design rules

These five are stated in the package docstring, and your lab code is expected to
follow them too.

| # | Rule | What it means in practice |
|---|---|---|
| 1 | **Provider-agnostic** | Model names are LiteLLM strings. Swapping Gemini for NVIDIA NIM or a local Ollama model changes one environment variable and no lab code. |
| 2 | **Everything is cached** | Identical requests never cost money twice. Re-running an evaluation is free. |
| 3 | **Everything is counted** | Tokens, cost and latency are recorded on every call, whether you asked or not. |
| 4 | **Everything is traceable** | Every call appends a JSONL trace record with a run id and a parent id. |
| 5 | **Offline-capable** | With `AIP_OFFLINE=1`, cached responses replay and an uncached request **raises loudly** rather than silently spending. |

Rule 5 is what makes the Lab 7 CI gate free and deterministic, and it is why the
response cache is committed to the repository.

---

## How the pieces fit

### The seven layers

T1 §4 claims every application in this module has the same seven-layer shape, and
that **layer 4 — the actual model call — is the smallest.** The package is
arranged so you can check that claim:

```
 7  INTERFACE       API / UI / batch job          labs/lab7/service.py, ui.py
 6  ORCHESTRATION   retries, routing, tool loop   llm.raw_call, guards.ToolGuard
 5  VALIDATION      schema, repair, guardrails    llm.structured, guards
 4  MODEL           the API call                  ~20 lines inside llm.raw_call
 3  CONTEXT         chunking, retrieval, prompts  chunking, retrieval, rag
 2  DATA            corpus, embeddings, cache     cache, embed
 1  OBSERVABILITY   traces, cost meter, evals     tracing, cost, evals
```

Layer 1 is not last. You build the meter before the engine — which is why Lab 2
is an evaluation lab and comes before any of the RAG labs.

### Dependency direction

One-way, no cycles, so any module can be read on its own.

| Module | Imports |
|---|---|
| `config` | — |
| `chunking` | — |
| `tracing` | `config` |
| `cache` | `config` |
| `cost` | `config` |
| `llm` | `cache`, `config`, `cost`, `tracing` |
| `embed` | `cache`, `config`, `cost`, `tracing` |
| `guards` | `tracing` |
| `evals` | `cost`, `llm`, `tracing` |
| `retrieval` | `chunking`, `embed`, `llm`, `tracing` |
| `rag` | `guards`, `llm`, `retrieval`, `tracing` |

Read left to right: `config` and `chunking` depend on nothing, `rag` sits on top
of almost everything.

### Which module matters in which lab

`*` = imported directly by that lab's starter code. `·` = in play underneath,
but you do not import it yourself.

| Module | L1 | L2 | L3 | L4 | L5 | L6 | L7 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `config` | · | · | · | · | · | · | **\*** |
| `llm` | **\*** | · | · | **\*** | · | **\*** | · |
| `cost` | **\*** | · | · | **\*** | · | **\*** | **\*** |
| `cache` | · | · | · | · | · | · | **\*** |
| `tracing` | · | · | · | · | · | · | **\*** |
| `evals` | **\*** | **\*** | **\*** | **\*** | · | · | · |
| `guards` | **\*** | · | · | **\*** | · | **\*** | · |
| `chunking` | · | · | **\*** | **\*** | · | **\*** | · |
| `embed` | · | · | · | · | · | · | · |
| `retrieval` | · | · | **\*** | **\*** | · | **\*** | · |
| `rag` | · | · | · | · | · | · | · |

Two modules are never imported by a lab and still matter:

- **`embed`** runs underneath every `DenseRetriever`. You will read it in Lab 3
  when you need to know what `input_type` does and why the cache key includes it.
- **`rag`** is a *reference implementation you read, then write your own version
  of.* Lab 4 tells you to write `ANSWER_SYSTEM` yourself **before** looking at
  `aip/rag.py`, then compare.

**Lab 5 imports nothing from `aip` directly** — it works on `reports/lab4.json`
and on your Lab 3 loaders. That is deliberate: it is a diagnosis lab, not a
building lab.

### Reading order

If you read the package straight through, this order costs the least
backtracking:

1. `config.py` — 10 min. Everything else resolves models through it.
2. `llm.py` — 30 min. **Read this one properly.** Lab 1 depends on knowing
   exactly what `structured()` does on your behalf.
3. `cost.py`, `cache.py`, `tracing.py` — 20 min together. Short, and they explain
   why re-runs are free and where the numbers come from.
4. `evals.py` — 30 min before Lab 2. It is the measuring instrument for the rest
   of the module; do not quote a number from an instrument you have not read.
5. `chunking.py`, `embed.py`, `retrieval.py` — 30 min before Lab 3.
6. `guards.py` — 15 min before Lab 6. All 159 lines.
7. `rag.py` — after you have written your own in Lab 4.

---

## Module reference

### `__init__.py` — the public surface

**29 lines.** Re-exports the handful of names most lab code needs, so the common
imports are one line.

```python
from aip import chat, structured, embed, Budget
```

| Re-exported | From |
|---|---|
| `MODELS`, `settings`, `resolve_model` | `config` |
| `Budget`, `BudgetExceeded`, `Usage` | `cost` |
| `chat`, `structured`, `StructuredOutputError` | `llm` |
| `embed`, `embed_batch` | `embed` |
| `trace`, `read_traces` | `tracing` |

Anything not in that list is imported from its module directly —
`from aip.retrieval import DenseRetriever`. The short list is a convenience, not
a boundary; nothing in the package is private to you.

---

### `config.py` — model tiers and settings

**175 lines.** The only place a model name is hard-coded. Everything else asks
for a *tier*.

| Name | What it is |
|---|---|
| `settings` | A `Settings` dataclass read from the environment at import |
| `MODELS` | The resolved `{tier: model-id}` mapping for the active profile |
| `resolve_model(name_or_tier)` | `"SMALL"` → a provider model string; passes real model ids through unchanged |

**The four tiers.** Lab code names a tier, never a model:

| Tier | Used for |
|---|---|
| `SMALL` | High-volume loops — extraction, per-item classification |
| `MAIN` | Quality-sensitive single calls — RAG answer generation |
| `LARGE` | Judging, and cascade escalation. **Deliberately a different family from `MAIN`** so an LLM judge is not grading its own generator |
| `EMBED` | Embeddings |

```python
from aip.config import settings, resolve_model
settings.profile          # 'gemini'
resolve_model("SMALL")    # 'gemini/gemini-3.5-flash-lite'
```

**Profiles.** `gemini` (default, every target in every handout is measured on it)
and `nvidia` are both verified end to end. `groq` is present but unverified;
`ollama` runs fully local at zero cost; `anthropic` and `openai` are paid.

**Used by:** Lab 7 directly, for `/health` and `/metrics`. Every other lab uses
it through `llm` and `embed` without importing it.

> **Worth knowing.** Model ids rot. Every id in the first version of this
> repository was dead within months, which is why `scripts/list_models.py`
> exists — and why "listed by the API" and "callable on your key" are different
> things. On NVIDIA, 83 models are listed and four respond.

---

### `llm.py` — the model client

**316 lines, and the one to read first.** Two functions you call, one you should
understand.

| Function | Returns |
|---|---|
| `chat(prompt, *, tier, system, max_tokens, temperature, return_full, ...)` | The text, or the full result dict with `return_full=True` |
| `structured(prompt, *, schema, tier, max_repairs=2, ...)` | A validated instance of your Pydantic model, or raises `StructuredOutputError` |
| `raw_call(messages, *, model, temperature, max_tokens, ...)` | The layer everything else goes through — retries, caching, cost, tracing |
| `extract_json(text)` | Tolerant JSON recovery from fenced or prose-wrapped output |

```python
from pydantic import BaseModel, Field
from aip import structured

class Ticket(BaseModel):
    category: Literal["billing", "claims", "technical"]
    urgency: int = Field(ge=1, le=5, description="1 = FAQ … 5 = emergency")

t = structured(ticket_text, schema=Ticket, tier="SMALL")
```

**What `structured()` does for you**, in order:

1. Requests provider-native JSON mode where available, falling back to plain text
   if the provider rejects it.
2. Serialises `schema.model_json_schema()` **into the system prompt** — which is
   why your `Field(description=…)` text reaches the model attached to the field
   it governs.
3. Parses tolerantly, stripping fences and surrounding prose.
4. Validates with Pydantic.
5. On failure, sends **the validation errors back to the model** and retries, up
   to `max_repairs`.
6. Treats truncation (`finish_reason == "length"`) separately and doubles the
   budget, because truncated JSON is not a schema problem and must not be
   "repaired" as one.

**Used by:** Lab 1 (`structured`, `StructuredOutputError`), Lab 4 and Lab 6
(`chat`). Underneath Labs 2, 3 and 5 as well.

> **The trap.** `structured()` validates **shape**, never **truth**. A perfectly
> valid record can still say `urgency: 1` about an ICU admission. And repairs are
> not free — every attempt goes through `raw_call`, so it is cached, counted and
> billed.

---

### `cost.py` — token accounting and budgets

**143 lines.** Every call is priced and counted; a `Budget` is a hard ceiling
that stops a run rather than quietly billing you.

| Name | What it does |
|---|---|
| `Budget(limit_usd, label)` | Context manager. Raises `BudgetExceeded` at the ceiling |
| `.report()` | The one-line summary you paste into a lab report |
| `Usage` | Per-call record: model, tokens, cost, latency, cached, priced |
| `is_priced(model)` | Can we state what this call cost? |
| `price_of(model, in, out)` | Cost in USD |
| `global_budget()` | The process-wide meter, used by Lab 7's `/metrics` |

```python
from aip.cost import Budget

with Budget(limit_usd=0.10, label="lab1-v0") as b:
    ...
print(b.report())
# [lab1-v0] calls=40 (cache hits 0%) tokens=6100in/1200out cost=$0.0006 \
#           latency p50=812ms p95=1204ms
```

**The three-way distinction that matters.** A model is *priced* (we know the
cost), *free* (`ollama/`, `local/` — `$0.00` is correct), or **unpriced** — a
paid API with no published per-token price. NVIDIA NIM is the third case, and the
report says so:

```
cost=$0.0006 + 1 UNPRICED call (nvidia_nim/...)
```

> **Why that exists.** The meter could have printed `$0.00` and looked tidy. A
> cost meter that silently reports zero for a paid API is exactly the class of
> bug this module teaches you to hate — so it refuses, and gives you token counts
> instead. Cost is proportional to tokens, so comparisons still rank correctly.

**Used by:** Labs 1, 4 and 6 wrap runs in a `Budget`; Lab 7 exposes
`global_budget()` through `/metrics`.

---

### `cache.py` — the content-addressed cache

**76 lines** over SQLite. The reason re-running an evaluation is free.

| Function | What it does |
|---|---|
| `make_key(kind, payload)` | SHA-256 over the normalised request |
| `get(key)` / `put(key, kind, request, response)` | Read / write |
| `stats()` | `{'chat': 3361, 'embed': 341}` |
| `clear(kind=None)` | Drop entries |

The key is the **whole request** — model, messages, temperature, and for
embeddings the `input_type`. That has two consequences you will meet:

- **Change any parameter and you get a new call**, correctly.
- **Do not change it and you get the old answer**, also correctly — which is the
  Lab 2 cascade bug. Two samples at temperature 0 are the *same request*, so the
  second is served from the cache, the answers are byte-identical, disagreement
  is never detected, and escalation reads 0%. Nothing errors. Drawing the second
  sample at temperature 0.8 changes both the sampling and the key.

With `AIP_OFFLINE=1` a miss raises `CacheMiss` instead of calling the provider.

**Used by:** Lab 7 directly (`/health` cache stats). Silently in every other lab —
and in CI, where the committed cache makes the Lab 7 regression gate free and
deterministic.

---

### `tracing.py` — JSONL spans

**85 lines.** A teaching-scale stand-in for Langfuse or LangSmith.

| Function | What it does |
|---|---|
| `trace(name, **attrs)` | Context manager; writes a span with a run id and parent id |
| `event(name, **attrs)` | A point-in-time record |
| `read_traces(run_id=None)` | Read them back |
| `trace_file()` | Path to the current JSONL file |

```python
from aip import trace
with trace("http.ask", question=q[:120]) as span:
    span["hits"] = len(hits)
```

Spans nest through the parent id, so one request decomposes into embed →
retrieve → generate → validate.

**Used by:** Lab 7 directly, where the bar is that traces alone must answer
*"why did request X take nine seconds?"* — a total is not a diagnosis, and two of
the likely causes (a repair retry, a rate-limit backoff) look like one slow call
in a start/end log.

---

### `chunking.py` — four chunking strategies

**119 lines.** Chunking is the biggest single lever on retrieval quality, and the
step most people skip in favour of tuning something more interesting.

| Function | Splits on | Costs you |
|---|---|---|
| `fixed_chunks(text, doc_id, size=800)` | Character count | Cuts mid-sentence, mid-rule |
| `sliding_chunks(..., overlap=150)` | Character count, with overlap | Duplication |
| `recursive_chunks(..., overlap=100)` | Paragraph → sentence → character | — |
| `markdown_chunks(..., size=1200)` | Headings, **prepending the heading path** | Needs real markdown |
| `STRATEGIES` | `{name: callable}`, for sweeping | |

A `Chunk` carries `text`, `doc_id`, `chunk_id` and a `meta` dict — and `meta` is
where Lab 3 puts `status: current | archived` for the metadata-filter exercise.

**Used by:** Lab 3 (the sweep), Lab 4 and Lab 6 (`markdown_chunks`, the winner).

> **Measured on this corpus.** At 800 chars: fixed 0.795, sliding 0.805,
> recursive 0.825, **markdown 0.846** nDCG@10. The heading-path prefix alone is
> worth **+0.054 nDCG@10 and +0.143 hit_rate@1** — and it *lowers* `hit_rate@5`,
> because it improves ranking, not recall.

---

### `embed.py` — embeddings

**136 lines.** Cached, batched, with a local fallback that needs no API key.

| Function | Notes |
|---|---|
| `embed_batch(texts, *, model, batch_size=64, input_type="passage")` | Returns an `(n, d)` array |
| `embed(text, *, model, input_type="query")` | One vector |
| `cosine(a, b)` | Similarity |

**Asymmetric embeddings.** Some models — NVIDIA NIM's, here — want to know
whether they are embedding a *query* or a *passage*, and produce different
vectors for the same text. The defaults are right for the common case: `embed()`
defaults to `query`, `embed_batch()` to `passage`. **`input_type` is part of the
cache key**, so the two never collide.

Vectors are stored base64 float32 rather than as JSON lists of floats. A
3072-dimensional vector is ~60 KB as JSON text and ~16 KB packed — across a
warmed corpus cache, the difference between a 44 MB file nobody wants in git and
a 12 MB one that makes `AIP_OFFLINE=1` work for everybody.

**Used by:** nothing imports it directly — it runs underneath every
`DenseRetriever`. Read it in Lab 3 when you want to know what the index actually
cost to build (about $0.008 for this corpus).

---

### `retrieval.py` — retrievers and rerankers

**238 lines.** Implemented over plain NumPy and `rank_bm25` rather than a
framework, because the whole point of Lab 3 is that you can see and change every
step.

| Class | What it is |
|---|---|
| `DenseRetriever(chunks)` | Embeddings + cosine. Exact, sub-millisecond at this scale |
| `Bm25Retriever(chunks)` | Lexical, term frequency × inverse document frequency |
| `HybridRetriever(retrievers, rrf_k=60, weights=None)` | Reciprocal Rank Fusion over **any number** of retrievers |
| `CrossEncoderReranker()` | Local `ms-marco-MiniLM-L-6-v2`; retrieve wide, rerank narrow |
| `LLMReranker()` | One model call per candidate |
| `ChromaRetriever(chunks, path=…)` | HNSW, persistence, and `where=` metadata filtering |
| `format_context(hits, max_chars=8000)` | **Numbered** source block for the answer prompt |
| `Hit` | `chunk`, `score`, `source`, `rank` — so a hybrid result stays explainable |

```python
from aip.retrieval import DenseRetriever, format_context
r = DenseRetriever(chunks)
hits = r.search("how long do I have to file?", k=8)
context = format_context(hits)          # "[1] …\n[2] …"
```

`format_context` numbering is load-bearing: the model can only legitimately cite
a number you supplied, so `[7]` with five sources is a **provable** error caught
by three lines of regex — no judge, no cost.

**Used by:** Lab 3 (all of it), Lab 4 and Lab 6 (`DenseRetriever`,
`format_context`), Lab 7 through your own pipeline.

> **Three measured results that contradict the textbook.** On this corpus hybrid
> **loses** to dense (0.830 vs 0.846); the cross-encoder **lowers** nDCG@10
> (0.804 → 0.788) because it is out of domain on policy prose; and HNSW ties on
> quality while being **3.6× slower** at 164 vectors. Lab 3 makes you measure all
> three yourself.

---

### `rag.py` — the reference RAG pipeline

**160 lines.** The seven stages, named, so you can point at the one that failed.

| Name | What it is |
|---|---|
| `RagPipeline(retriever, reranker=None, ...)` | `.retrieve()` · `.rerank()` · `.generate()` · `.answer()` |
| `RagAnswer` | `answer`, `hits`, `citations_valid`, `invalid_citations`, `refused`, `stages` |
| `ANSWER_SYSTEM` | The reference answer prompt |
| `REFUSAL` | The exact refusal string, so a refusal is machine-detectable |
| `hyde(question)` | Hypothetical document embedding — a query-side transform |
| `multi_query(question, n=3)` | Decompose into sub-questions |

**`stages` is the point.** It records what each stage did, which is what makes
the Lab 5 failure classification possible at all.

**Used by:** nothing imports it. **Lab 4 tells you to write `ANSWER_SYSTEM`
yourself first, then compare with this file and note the differences.** Reading
it before you have tried is the one way to get less out of Lab 4 than you
should.

---

### `evals.py` — the evaluation harness

**376 lines — the largest module, and the most important.** Read all of it before
Lab 2.

**Deterministic metrics** — free, unarguable, and always preferred:

| Function | Returns |
|---|---|
| `exact_match(pred, gold)` | |
| `field_accuracy(pred, gold, fields)` | Per-field **and** `record_accuracy` |
| `json_valid(pred)` | |
| `retrieval_metrics(retrieved, relevant, ks=(1,3,5,10))` | `hit_rate@k`, `recall@k`, `MRR`, `nDCG@k` |

**LLM-as-judge** — for what has no deterministic test:

| Name | Notes |
|---|---|
| `JUDGE_RUBRIC_FAITHFULNESS`, `JUDGE_RUBRIC_CORRECTNESS` | Single-criterion, deliberately improvable |
| `llm_judge(prompt, tier="LARGE", max_tokens=2048)` | Retries once at double the budget on truncation; returns `parse_error` rather than a score |
| `judge_agreement(judge, human)` | **Cohen's κ.** You may not report a judged number without it |

**The runner:**

| Name | Notes |
|---|---|
| `Case`, `CaseResult`, `EvalReport` | `id` / `input` / `expected`; results carry metrics, error and latency |
| `run_eval(name, cases, system, metric, *, budget_usd, workers=4)` | Threaded, budgeted, traced |
| `compare(*reports, metrics=...)` | The side-by-side table |
| `load_cases(path)` | JSONL → `list[Case]` |
| `EvalReport.aggregate() / .summary() / .failures(metric) / .save(path)` | |

```python
from aip.evals import load_cases, run_eval, field_accuracy
cases = load_cases("data/eval/extraction_dev.jsonl")
rep = run_eval("lab1-c", cases, extract_c,
               lambda p, g: field_accuracy(p, g, FIELDS), budget_usd=0.30)
print(rep.summary())
```

**Used by:** Labs 1, 2, 3 and 4 directly. Lab 5 consumes its saved output.

> **The war story, and it is in this file.** Faithfulness was first measured at
> **0.667** when the true value was **0.933**. `llm_judge` capped output at 512
> tokens; the judge tier is a reasoning model that spent most of that budget on
> invisible thinking, so its verdict was truncated mid-object, failed to parse —
> **and the parse failure was scored 0.** Nothing errored. The rule it produced
> is now enforced here: *a parse failure is missing data, not a failing answer.*
> Check what your own harness does with one before you trust any number it gives
> you.

---

### `guards.py` — guardrails for untrusted input

**159 lines.** Everything here is a **layer, not a solution.** There is no known
complete defence against prompt injection; the goal is to raise the cost of an
attack and make a successful one visible.

| Name | Layer |
|---|---|
| `redact_pii(text)` | Typed placeholders + counts |
| `detect_injection(text)` → `InjectionVerdict` | Heuristic signatures: override, role switch, exfiltration |
| `delimit_untrusted(content, label)` | Wraps content **and strips the closing tag from it** |
| `UNTRUSTED_SYSTEM_CLAUSE` | The system-prompt half of that layer |
| `ToolGuard(max_calls, allow, requires_confirmation, confirm_fn)` | Call budget, allowlist, human confirmation; raises `ToolDenied` |
| `enforce_citations(answer, n_sources)` | `(ok, invalid_indices)` |

The controls map onto the OWASP Top 10 for LLM Applications — LLM01 prompt
injection, LLM02 insecure output handling, LLM06 sensitive information
disclosure, LLM10 unbounded consumption — and the module docstring says which.

**Used by:** Lab 1 (the PII patterns, for the `contains_pii` field), Lab 4
(`delimit_untrusted`), Lab 6 (all of it).

> **Two things to notice.** `delimit_untrusted` strips the closing tag from the
> content — without that, an attacker simply closes your tag early and writes
> outside it, and *a delimiter you do not enforce is decoration.* And
> `detect_injection` is a **classifier**, so it has two error rates: it is where
> your false positives come from, because ordinary English contains the words it
> looks for.

---

## Configuration and environment

Everything is read from the environment at import, via `.env` in the repo root.

| Variable | Default | What it does |
|---|---|---|
| `AIP_PROFILE` | `gemini` | Which provider profile the tiers resolve against |
| `AIP_BUDGET_USD` | `2.0` | Hard per-process ceiling. Trips `BudgetExceeded` |
| `AIP_CACHE` | `1` | Identical requests are free and instant |
| `AIP_OFFLINE` | `0` | `1` = replay only; a miss raises instead of spending |
| `AIP_TEMPERATURE` | `0.0` | Deterministic by default |
| `AIP_TIMEOUT_S` | `60` | Per-call timeout |
| `AIP_CACHE_DIR` | `.aip_cache` | |
| `AIP_TRACE_DIR` | `.aip_traces` | |
| `AIP_RUN_ID` | generated | Set it to group traces across processes |

Plus exactly one provider key — `GEMINI_API_KEY`, `NVIDIA_API_KEY`, and so on.
`.env` is gitignored and must never be committed.

```bash
make check      # verify the environment and make one live call
make offline    # the same check in replay mode; costs nothing
make cost       # what you have spent, and what is cached
```

---

## Extending or replacing a module

The package is a starting point, not a boundary. Some things students do, and
where they belong:

| You want to | Do this |
|---|---|
| Add a provider | A new entry in `PROFILES` in `config.py`. Nothing else changes |
| A different chunker | A function with the same signature, added to `STRATEGIES` |
| A different retriever | Subclass `Retriever` and implement `.search(query, k)` |
| A different vector store | Same — `ChromaRetriever` is the worked example |
| A new metric | A callable `(pred, gold) -> dict[str, float]`, passed to `run_eval` |
| A new guard layer | A function over the untrusted text, or a `ToolGuard` field |

Two rules if you do:

1. **Keep the tier indirection.** Hard-coding a model id in lab code breaks the
   provider portability that makes the module free to run.
2. **Do not bypass `raw_call`.** Calling `litellm` directly loses caching, cost
   accounting, retries and tracing all at once — and the numbers in your report
   come from those.
