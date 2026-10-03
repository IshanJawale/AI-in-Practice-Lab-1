# Lab 7 — the code: what is provided, and every TODO

Five files, and this is the lab where **everything you have built so far gets
imported at once**. Most of your work is wiring, not writing.

> `aip/` is the toolkit — read it, never change it. `labs/` is your system.
> By now that also means **your own earlier labs are your dependencies.**

---

## What you will call — from `aip/`, and from yourself

| You need | Where it lives | Signature / note |
|---|---|---|
| Your retrieval configuration | **`labs/lab3/search.py`** | your Lab 3 winner |
| Your answer pipeline | **`labs/lab4/rag.py`** | `answer_question(...)` |
| Your Lab 5 fix | **`labs/lab5/diagnose.py`** | whatever you shipped |
| Your tool loop and guards | **`labs/lab6/agent.py`** | `run_agent(...)`, `ToolGuard` |
| A complete reference pipeline, if yours is not ready | `aip.rag` | `RagPipeline` |
| Per-request traces | `aip.tracing` | `trace(name, **fields)`, `read_traces()` |
| Cost and latency accounting | `aip.cost` | `Budget(...)`, `global_budget().report()` |
| Cache statistics for `/health` | `aip.cache` | `stats()` |
| Guards on the request path | `aip.guards` | `ToolGuard`, `delimit_untrusted`, `enforce_citations` |
| Metrics for the gate | `aip.evals` | `run_eval`, `llm_judge`, `retrieval_metrics` |

> **`aip.tracing` is what makes Part C possible.** Everything in `aip/` already
> emits spans — `llm.call`, `retrieve.dense`, `guard.*`. You are not building
> tracing; you are reading it and adding spans for your own stages.

---

## `service.py` — the API

### Provided
`app = FastAPI(...)`, and the Pydantic models `AskRequest`, `Citation`,
`AskResponse`. **Read `AskResponse` first — it is the contract, and it tells
you what the rest of the lab expects.**

### `pipeline()` — **TODO A2**
Build your Labs 3–5 pipeline **once, at startup, and cache it.**

> Building it per request re-embeds the corpus on every call. It is the single
> most common reason a service is slow for no apparent reason.

Wire your **Lab 6 guards** in here too. A service with no guards is not
shippable, and this is where marks go.

### `POST /ask` — **TODO A1**
Return `cost_usd` and `trace_id` **in the response body.**

### Error handling — **TODO A3**
The TODO in the exception handler asks you to distinguish:

| Cause | Status | Extra |
|---|---|---|
| Malformed request | 422 | FastAPI gives you this free — verify it |
| Provider outage | **503** | `Retry-After` header |
| Budget exhausted (`BudgetExceeded`) | **429** | |

Everything else may be a 500 — but a provider outage arriving as a 500 with a
stack trace is a defect.

### `GET /health`, `GET /metrics`
`/health`: index size, model, cache stats (`aip.cache.stats()`).
`/metrics`: cost today, cost/query, cache hit rate, p50/p95/p99, **error rate
by type**, tool-call counts — all derivable from `aip.tracing.read_traces()`.

### `POST /ask/stream` — **Part B2**
Server-sent events. `sse-starlette` is already in `requirements.txt`.

---

## `ui.py` — the demo surface

### **TODO A4**
Render citations as **expanders showing the source excerpt.**

> Grounding is only useful if the user can check it. A citation marker nobody
> can expand is decoration.

### TODO (stretch)
A thumbs-down button that appends the case to a review queue — the cheapest
real feedback loop there is.

---

## `dashboard.py` — observability

### **TODO C3**
p50/p95 **per span name**. This is the table that answers *"why did request X
take 9 seconds?"* — which is the question Part C exists for.

Minimum: latency by stage over time, cumulative cost, error rate, cache hit rate.

### **TODO C4**
**One** alert condition, and what you would do when it fires. The best one on
this system is **refusal rate doubling** — it almost always means the index
broke, and no quality metric will tell you that as quickly.

---

## `gate.py` + `thresholds.yml` — the regression gate

### `measure()` — **TODO D1**
Run your golden set, return a metric dict whose keys match `thresholds.yml`:

```yaml
correctness: {min: 0.75}        faithfulness:      {min: 0.90}
citation_validity: {min: 0.98}  refusal_recall:    {min: 0.80}
refusal_precision: {min: 0.75}  hit_rate_at_5:     {min: 0.85}
cost_per_query_usd: {max: 0.010}  p95_latency_ms:  {max: 6000}
```

`main()` compares and returns the exit code — provided.

> **Tune the thresholds to just below what you actually achieve.** At your
> current number it fails on noise; far below it never fires. About one
> standard error of headroom.
>
> **Note that cost and latency are gated too.** They regress silently otherwise
> — nothing gets *wrong*, it just gets expensive.

### `.github/workflows/eval.yml` — provided
Runs with **`AIP_OFFLINE=1`** against your committed cache, so **CI needs no
API key and costs nothing.** You must commit the cache for this to work.

---

## The traps

1. **Building the pipeline per request.** Slow for no visible reason.
2. **Shipping without the Lab 6 guards.** Explicitly graded.
3. **Semantic caching without finding its breaking threshold.** It does not
   error — it answers a *different question*. Find the threshold, report it.
4. **Streaming before validating.** You cannot un-send an answer. B3 is a real
   design decision with no free option.
5. **A gate you have never seen fail.** D3 exists for this.
6. **Leaving Part E to the last ten minutes.** It is 16% of the module.

## Common errors

| Symptom | Cause |
|---|---|
| `NotImplementedError("wire in your pipeline")` | `pipeline()` — TODO A2 |
| Every request takes seconds | Pipeline built per request |
| Outage returns 500 | TODO A3 |
| CI fails on a missing key | Needs `AIP_OFFLINE=1` and a committed cache |
| `/metrics` is empty | No traces written yet, or reading the wrong directory |
| Gate passes after you broke something | Thresholds too loose |
