# Lab 7 — Concepts
### Keep this open while you work

| Concept | In the code | In the theory |
|---|---|---|
| The seven-layer architecture | your whole service | T1 §4 |
| API contract design | `service.py` | — |
| Status-code semantics | your A3 | T1 §2.4 |
| Exact response cache | `aip/cache.py` | T1 §2.3 |
| Semantic cache | your B1 | T1 §4.1 |
| Streaming and TTFT | your `/ask/stream` | T1 §2.2 |
| Tracing and spans | `aip/tracing.py` | T1 §4 layer 1 |
| Percentiles and SLOs | `/metrics` | T1 §2.2, §4.1 |
| Alert design | your C4 | T1 §4.1 |
| Regression gates | `gate.py`, `thresholds.yml` | T3 §5.3 |
| Offline replay | `AIP_OFFLINE=1` | T1 §4.1 |
| Reproducibility | your committed cache | universal rubric |

---

## The seven-layer architecture

**What it is.** Every application in this module has the same shape, and today
you assemble all of it:

```
 1  OBSERVABILITY   traces, cost, evals        aip/tracing.py, aip/cost.py
 2  DATA            corpus, cache, embeddings  aip/cache.py, aip/embed.py
 3  CONTEXT         chunking, retrieval, RAG   aip/chunking.py, retrieval.py, rag.py
 4  MODEL           the API call               ~20 lines inside aip/llm.py
 5  VALIDATION      schemas, guards            aip/llm.py::structured, aip/guards.py
 6  ORCHESTRATION   retries, tool loop         aip/llm.py::raw_call, ToolGuard
 7  INTERFACE       the service and the UI     labs/lab7/
```

**In the theory.** T1 §4.

**The claim it makes.** Layer 4 is the smallest layer and the only stochastic
one. If most of your code is in layer 4, you have built a demo. Your service is
the evidence for or against that claim — go and count.

---

## API contract design

**What it is.** `POST /ask` returns `{answer, citations[], sources[],
latency_ms, cost_usd, cached, trace_id}`.

**Not in the lectures**, and mostly ordinary web engineering — except for two
fields that are not.

**`cost_usd` and `trace_id` are in the response body on purpose.** The trace id
is how someone debugging in production finds the trace for one bad answer from
yesterday; without it you are grepping logs by timestamp. The cost is how the
person paying for the system sees what a query costs, without reading your
dashboard. Both are the module's instincts — measure the triple, make the system
inspectable — arriving in an HTTP contract.

---

## Status-code semantics

Each code tells the caller something different about **what to do next**:

| Situation | Code | Because |
|---|---|---|
| Malformed request | **422** | Your request was wrong. Do not retry it unchanged |
| Model provider outage | **503** + `Retry-After` | We are down; retry, and here is when |
| Budget exhausted | **429** | You are over your allowance. Back off |
| Anything with a stack trace | **never 500** | Says nothing useful and leaks internals |

**In the theory.** T1 §2.4, as graceful degradation.

---

## Caching: two layers, two risk profiles

### Exact response cache

Key: a hash of the normalised question. **A hit is the same question**, so it
cannot be wrong. Typical hit rate 15–30%; saves everything.

**In the code.** `aip/cache.py::make_key` — content-addressed SQLite.

### Semantic cache *(T1 §4.1)*

Key: the **embedding** of the question. A hit is a question whose embedding is
within a cosine threshold of a previous one. Adds perhaps 10–20 points of hit
rate — and **can return an answer to a different question**.

**Why it is the feature most likely to silently break your system.** Consider:

```
"What is the waiting period on Gold?"      cosine ≈ 0.97
"What is the waiting period on Silver?"  <- different answer
```

Below the safe threshold, the cache returns a confident, well-cited, **fast**
answer to a question nobody asked. Your latency improves. Your cost improves.
Correctness quietly falls, and nothing errors.

**The threshold is the deliverable, not the feature.** Sweep it: for each
candidate value, take pairs above it and check whether the cached answer is
actually right for the new question. Find where the wrong hits begin. **It is
lower than people assume.** The `0.95` in the starter is *reasoned, not
measured*, and the comment in the file says so — reproducing a number you did
not measure is the thing this module penalises hardest.

**Two mitigations worth knowing:** raise the threshold and accept a lower hit
rate; or key the cache on the question **plus** any filters, so questions
differing only in a plan name never collide.

---

## Streaming, TTFT, and the validation problem

**What it is.** Server-sent events: tokens go to the client as they are
generated. **TTFT** — time to first token — is what the user experiences as
responsiveness, and it is nearly independent of total time.

**In the theory.** T1 §2.2.

**Why it helps so much here.** Output tokens are generated **serially**, so a
5-second answer feels like 5 seconds of nothing. Streaming turns that into ~1
second of nothing followed by text arriving. Total time is unchanged; the
experience is not.

**The problem it creates.** You cannot validate citations until the answer is
complete — and you have already sent it. Three defensible resolutions:

| Option | Costs you |
|---|---|
| Buffer, validate, then stream | The entire TTFT benefit |
| Stream, then send a validation event the UI acts on | UI complexity; the user may already have read it |
| Stream the prose, hold citations to the end | Grounding arrives late |

**Choose one and defend it.** What is graded is the defence.

---

## Percentiles, and what an SLO is

**What it is.** p50 is the median; **p95** is the value 95% of requests come in
under; p99 is the tail.

**In the theory.** T1 §2.2 for p95, T1 §4.1 for the SLO discipline.

**Why not the mean.** Latency distributions are long-tailed — a repair retry, a
rate-limit backoff, a cache miss. A mean of 900 ms with a p95 of 6 s is a system
that feels broken to **one user in twenty**, and the mean cannot see them.

**An SLO** is a threshold you commit to on a percentile — *"p95 under 6 s,
uncached"*. It is a promise, not a measurement, and it is what an alert and a
regression gate are both defined against.

**Quote cached and uncached separately.** They are different systems: a cache
hit skips retrieval and generation entirely. A blended p95 moves when your
traffic mix moves, and it lets a high hit rate hide a slow cold path.

**Break p95 down by stage** and you will find generation is ~98% of it — which
hands you a real decision rather than a free win, because the biggest generation
lever is answer length, and Lab 5 measured what shortening it costs.

---

## Alert design *(T1 §4.1)*

**What it is.** A condition on a metric that pages someone, plus what they do
when it fires. An alert with no action attached gets ignored within a week.

**Three candidates, and why the third is the best:**

| Alert | Catches | Weakness |
|---|---|---|
| p95 above SLO for 5 min | Slow provider, bad deploy | The 5 min matters — a single slow request is not an incident |
| Cost per hour above budget | Runaway loops, a retry storm | Lags; damage is done |
| **Refusal rate doubling** | **A broken or stale index** | Also fires on a genuinely odd traffic day |

**Why the refusal-rate alert is the interesting one.** A broken index throws no
errors, raises no latency, and costs no more. It just quietly stops finding
things — and a correctly built RAG system responds by **declining**. The refusal
rate is where a silent data failure becomes visible, and watching it is free.

**The general principle:** the best alerts watch the *symptom the system
produces when it fails silently*, not the failures it already logs.

---

## Regression gates

**What it is.** A CI job that runs your golden set on every push and exits
non-zero if any metric breaches its threshold.

**In the code.** `gate.py` and `thresholds.yml`.

**In the theory.** T3 §5.3.

**Why the thresholds include cost and latency, not just quality.** A change that
swaps `SMALL` for `LARGE` passes every quality check and multiplies your annual
bill — and Lab 2 measured that exact change as not detectably better. The gate
is where the trade-offs you argued for become enforceable.

**Directional thresholds:**
```yaml
correctness:        min 0.75      # floors on quality
citation_validity:  min 0.98
cost_per_query_usd: max 0.010     # ceilings on cost and latency
p95_latency_ms:     max 6000
```

**A gate you have not seen fail is a gate you do not have.** Break something
deliberately — `final_k = 1`, or delete a corpus document — and show the red
build. An eval that never runs, a threshold that is unreachable, and a swallowed
exit code all produce **the same green tick** as a working gate. You have seen
this failure twice already: Lab 2's cascade reporting 0% escalation while
appearing to work, and Lab 4's judge scoring parse failures as zero.

---

## Offline replay *(T1 §4.1)*

**What it is.** `AIP_OFFLINE=1` makes every model call read from the committed
response cache and **fail loudly** rather than hitting the network.

**In the code.** `aip/cache.py`, `aip/llm.py::raw_call`.

**What it buys.**

- **CI needs no API key and costs nothing** — which is what makes running the
  eval on every push realistic rather than aspirational.
- **The eval is deterministic** run to run, so a red build means your code
  changed, not that the model had an off day.
- **A grader can reproduce your numbers** from a clean clone.

**What it requires of you.** The cache is **part of the artefact**. Commit it,
and keep it current with your pipeline — a cache that no longer covers your
prompts turns every CI run red for the wrong reason.

**The trap.** Offline replay proves your *pipeline* is reproducible. It proves
nothing about whether the provider still behaves that way. Both matter; they are
different questions.
