# Lab 7 — Ship It
**3 hours · Pairs · Integration and Demo Day**

> **Read [`OVERVIEW.md`](OVERVIEW.md) first** — why this lab exists, how to
> approach the three hours, the hints, and the map back to the theory
> sessions. Keep [`CONCEPTS.md`](CONCEPTS.md) open while you work.
> This file is the detail.

---

## The problem

Six labs of components. Nobody outside this room can use any of them.

Today you ship: an HTTP service, running, with caching, streaming, tracing, a
cost dashboard, a regression gate, and an evaluation report that defends its
behaviour with numbers.

This is the deliverable that goes in your portfolio, and it is the one that
gets you hired. Every candidate has a RAG notebook. Almost none has a RAG
service with a p95 SLO and a CI gate on eval regression.

### Targets

| Requirement | Target |
|---|---|
| `POST /ask` returns a grounded answer with citations | working |
| `GET /health` reports index size, model, cache stats | working |
| `GET /metrics` returns cost, latency percentiles, call counts | working |
| Streaming endpoint | TTFT ≤ 1,500 ms |
| p95 end-to-end latency, cached | ≤ 800 ms |
| p95 end-to-end latency, uncached | ≤ 6,000 ms |
| Cost per query | ≤ $0.01 |
| Regression gate | fails the build when any key metric drops beyond tolerance |
| Evaluation report | complete, honest, with a limitations section |

---

## Timetable

| Time | Part | What you do |
|---|---|---|
| 0:00–0:50 | **A** | The service |
| 0:50–1:20 | **B** | Caching, streaming, and the latency budget |
| 1:20–1:50 | **C** | Observability: traces, cost dashboard |
| 1:50–2:15 | **D** | The regression gate |
| 2:15–2:35 | **E** | The evaluation report |
| 2:35–3:00 | **Demo day** | 5 minutes per pair, live, with your metrics on screen |

---

## Part A — The service (50 min)

`labs/lab7/service.py` has the FastAPI skeleton.

**A1.** `POST /ask` → `{question, top_k?, mode?}` → `{answer, citations[],
sources[], latency_ms, cost_usd, cached, trace_id}`.

Return the cost and the trace id **in the response**. This is not padding — it
is how anyone debugging your system in production finds the trace, and it is
how the person paying for it sees what a query costs.

**A2.** Wire in your best pipeline from Labs 3–5, and your Lab 6 guards. Both.
A service with no guards is not shippable, and this is where marks are lost.

**A3.** Error handling. A malformed request gets a 422. A model outage gets a
503 with a `Retry-After`, not a 500 with a stack trace. A budget exhaustion
gets a 429. Test all three with `curl`.

**A4.** Add the Streamlit UI (`labs/lab7/ui.py`) so the demo is not `curl`.
It must show the citations as expandable source text — grounding is only
useful if the user can check it.

---

## Part B — Caching and streaming (30 min)

**B1. Two cache layers, and know why they are different:**

| Layer | Key | Hit rate | Saves |
|---|---|---|---|
| Exact response cache | hash of the normalised question | 15–30% | everything |
| Semantic cache | embedding of the question, cosine ≥ 0.95 | +10–20% | everything, at the risk of a wrong hit |

Implement the exact cache. Then implement the semantic cache **and find the
threshold at which it starts returning wrong answers.** Report that threshold —
it is the interesting number, and it is lower than people assume. Semantic
caching is the feature most likely to silently break your system.

**B2. Streaming.** Add `POST /ask/stream` with server-sent events. Report TTFT
and total, and note the difference from the non-streaming path.

**B3.** Then face the problem streaming creates: **you cannot validate
citations until the answer is complete, but you have already sent it.** Choose
and defend one of:
- buffer, validate, then stream (loses the TTFT benefit)
- stream, then send a validation event the UI acts on
- stream the prose, hold the citations to the end

**B4. The latency budget.** Break down p95 by stage from your traces:

```
embed query      __ ms
retrieve         __ ms
rerank           __ ms
generate         __ ms
validate         __ ms
─────────────────────
total            __ ms
```

Then state which stage you would optimise first, and what you would do.

---

## Part C — Observability (30 min)

**C1.** Every request writes a trace (`aip.tracing`). Confirm you can answer,
from traces alone: *"why did request X take 9 seconds?"*

**C2.** `GET /metrics`: total cost today, cost per query, cache hit rate,
latency p50/p95/p99, error rate by type, tool-call counts.

**C3.** Build the dashboard (`labs/lab7/dashboard.py`) — a Streamlit page
reading the trace files. Minimum: latency by stage over time, cost cumulative,
error rate, cache hit rate.

**C4.** Add one alert condition and say what you would do when it fires.
Examples: p95 above SLO for 5 minutes; cost per hour above budget; refusal rate
doubling (which usually means the index broke).

---

## Part D — The regression gate (25 min)

**D1.** `labs/lab7/gate.py` runs your golden set and exits non-zero if any
metric breaches:

```yaml
correctness:        min 0.75
citation_validity:  min 0.98
refusal_recall:     min 0.80
cost_per_query_usd: max 0.010
p95_latency_ms:     max 6000
```

**D2.** Wire it into GitHub Actions (`.github/workflows/eval.yml`, provided).
It runs with `AIP_OFFLINE=1` against your committed cache, so CI needs no API
key and costs nothing. Commit the cache.

**D3.** Prove it works: **deliberately break something** — drop `final_k` to 1,
or delete a corpus document — push, and show the red build. A gate you have not
seen fail is a gate you do not have.

---

## Part E — The evaluation report (20 min)

Two pages. This is 16% of Module 1 on its own.

1. **What it does** — one paragraph, no jargon. A non-engineer must understand it.
2. **How well it works** — the full metric table on the test questions.
3. **Where it fails** — the remaining failure modes with counts. Be specific.
4. **What it costs** — per query, per 1,000 queries, per year at 10,000/day.
5. **How fast it is** — p50/p95, broken down by stage.
6. **What it is not safe for** — the honest limitations section.
7. **What you would do next** — three things, ranked, with expected value.

Section 6 is the one that distinguishes a professional report. Every system has
a boundary of safe use. If you cannot state yours, you do not understand your
own system. Ours, for instance, should not be relied on for a coverage decision
without human review, and you should be able to say precisely why.

---

## Demo day (25 min)

Five minutes per pair. Live, on the projector.

1. Ask a question it answers well. (30 s)
2. Ask a question it refuses, and explain why refusal is correct. (30 s)
3. Show `/metrics` — real cost, real latency. (1 min)
4. Show the regression gate failing on a deliberate break. (1 min)
5. Show your worst remaining failure and say what you would do about it. (1 min)
6. Questions. (1 min)

Item 5 is graded. Every system has one; a pair that claims otherwise has not
looked.

---

## Deliverables

1. `labs/lab7/` — service, UI, dashboard, gate, workflow
2. `EVALUATION_REPORT.md` — the two-pager
3. `README.md` at your repo root — how to run it in under five minutes on a
   clean machine. Test this on your partner's laptop, not yours.
4. Your committed cache, so CI and graders can run offline

---

## Rubric (Lab 7 capstone: 20% + evaluation report: 16% of Module 1)

**System (20%)**

| Criterion | Weight |
|---|---|
| Service works, meets the latency and cost budgets | 30% |
| Caching (both layers) with the semantic threshold reported | 15% |
| Streaming, with the B3 validation problem addressed | 15% |
| Observability: traces answer real questions; dashboard works | 20% |
| Regression gate, demonstrated failing | 20% |

**Evaluation report (16%)**

| Criterion | Weight |
|---|---|
| Metrics complete and reproducible from your committed artefacts | 30% |
| Cost and latency analysis with the stage breakdown | 20% |
| Failure analysis is specific and quantified | 20% |
| Limitations section is honest and concrete | 20% |
| Next steps ranked with expected value | 10% |

---

## Stretch

1. **Load test.** 20 concurrent users with `locust`. Where does it break, and
   what breaks first? (It will be rate limits, not your code.)
2. **A/B in production.** Route 50% of traffic to a variant, log both, compare.
3. **Feedback loop.** A thumbs-down button that writes the case into a review
   queue. This is how real golden sets get built.
4. **Docker + deploy.** Containerise and deploy to a free tier. Report cold-start.
5. **Per-user access control.** Tag chunks with a `visibility` field; filter at
   query time by the caller's role. Then verify with a test that a restricted
   user cannot retrieve a restricted chunk — including by asking cleverly.
