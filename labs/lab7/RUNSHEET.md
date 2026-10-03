# Lab 7 — Runsheet

**Follow this top to bottom.** Every step says *why*, *what*, *how*, and how you
know you are finished.

| | |
|---|---|
| [`OVERVIEW.md`](OVERVIEW.md) | **why** — read before the lab |
| [`README.md`](README.md) | **the brief** — targets, deliverables, rubric |
| [`CONCEPTS.md`](CONCEPTS.md) | **the reference** — concept → code → theory |
| [`CODE_GUIDE.md`](CODE_GUIDE.md) | **the files** — five of them; every TODO itemised |
| this file | **the actions** |

**Pairs.** The last 25 minutes are **demo day**, live on the projector.

---

## ⚠️ This lab is 36% of Module 1

**20% for the system, 16% for the evaluation report.** More than any other lab,
and more than twice most of them. Budget your three hours accordingly — and
note that **Part E is 16% and gets 20 minutes.** Do not let it be the thing you
run out of time for.

---

## The lab in one line

> Six labs of components, and nobody outside this room can use any of them.
> Today it becomes a service — with an SLO, a cost meter, and a CI gate.

---

## Before you sit down

- [ ] Your best pipeline from Labs 3–5 identified, and it runs
- [ ] Your Lab 6 guards identified — **both go in; a service with no guards is
      not shippable, and this is where marks are lost**
- [ ] `make check` clean
- [ ] `reports/lab4.json` and your Lab 5 numbers to hand — Part E quotes them

---

# 1 · Part A — the service — 50 min

**Why.** A notebook is not a system. Everyone has a RAG notebook; almost nobody
has a RAG service with a p95 SLO and a CI gate.

**1.1 — `A1`.** `POST /ask` → `{question, top_k?, mode?}` →
`{answer, citations[], sources[], latency_ms, cost_usd, cached, trace_id}`.

> **Return `cost_usd` and `trace_id` in the response.** Not padding: it is how
> someone debugging in production finds the trace, and how the person paying
> sees what a query costs.

**1.2 — `A2`.** Wire in your Labs 3–5 pipeline **and** your Lab 6 guards. Build
it **once at startup**, not per request.

**1.3 — `A3`.** Error handling, and **test all three with `curl`**:

| Situation | Response |
|---|---|
| Malformed request | **422** |
| Model outage | **503** with `Retry-After` — *not* a 500 with a stack trace |
| Budget exhausted | **429** |

**1.4 — `A4`.** The Streamlit UI, so the demo is not `curl`. Citations must be
**expandable source text** — grounding is only useful if the user can check it.

> **Done when:** all three error cases return the right status, and `/ask`
> returns a cost and a trace id you can actually look up.

---

# 2 · Part B — caching, streaming, the budget — 30 min

**2.1 — `B1`. Two cache layers, and know why they differ:**

| Layer | Key | Hit rate | Risk |
|---|---|---|---|
| Exact | hash of the normalised question | 15–30% | none |
| Semantic | question embedding, cosine ≥ 0.95 | +10–20% | **a wrong hit** |

Implement the exact cache. Then the semantic cache — **and find the threshold
at which it starts returning wrong answers.**

> **Report that threshold. It is the interesting number, and it is lower than
> people assume.** Semantic caching is the feature most likely to silently
> break your system: it does not error, it just answers a different question.

**2.2 — `B2`.** `POST /ask/stream` with server-sent events. Report **TTFT** and
total, and the difference from the non-streaming path.

**2.3 — `B3`. Then face the problem streaming creates.** You cannot validate
citations until the answer is complete — **and you have already sent it.**
Choose one and defend it:

- buffer, validate, then stream — loses the TTFT benefit
- stream, then send a validation event the UI acts on
- stream the prose, hold the citations to the end

**2.4 — `B4`. The latency budget**, from your traces:

```
embed query  __ · retrieve __ · rerank __ · generate __ · validate __  =  total __ ms
```

Then say which stage you would optimise first, and what you would do.

---

# 3 · Part C — observability — 30 min

**Why.** If you cannot answer *"why did request X take 9 seconds?"* from traces
alone, you do not have observability — you have logging.

**3.1 — `C1`.** Every request writes a trace (`aip.tracing`). **Test the
question above on a real slow request.**

**3.2 — `C2`.** `GET /metrics`: cost today, cost per query, cache hit rate,
latency p50/p95/p99, error rate **by type**, tool-call counts.

**3.3 — `C3`.** The dashboard — Streamlit over the trace files. Minimum:
latency by stage over time, cumulative cost, error rate, cache hit rate.

**3.4 — `C4`.** **One** alert condition, and what you would do when it fires.
Good candidates: p95 above SLO for 5 minutes · cost per hour above budget ·
**refusal rate doubling**, which usually means the index broke.

---

# 4 · Part D — the regression gate — 25 min

**Why.** Every metric you are not gating will regress, quietly, and you will
find out from a user.

**4.1 — `D1`.** `gate.py` runs your golden set and **exits non-zero** on any
breach of `thresholds.yml`.

> Tune the thresholds to **just below what you actually achieve.** A gate set
> at your current number fails on noise; one set far below never fires. Aim for
> about one standard error of headroom.
>
> **Cost and latency have gates too.** They regress silently otherwise.

**4.2 — `D2`.** Wire it into GitHub Actions — `.github/workflows/eval.yml` is
provided. It runs with `AIP_OFFLINE=1` against your committed cache, so **CI
needs no API key and costs nothing.** Commit the cache.

**4.3 — `D3`. Prove it works. Deliberately break something** — drop `final_k`
to 1, or delete a corpus document — push, and **show the red build.**

> ### A gate you have not seen fail is a gate you do not have.

---

# 5 · Part E — the evaluation report — 20 min

**This is 16% of Module 1 on its own.** Two pages, seven sections:

1. **What it does** — one paragraph, no jargon. A non-engineer must follow it
2. **How well it works** — the full metric table
3. **Where it fails** — remaining failure modes, with counts. Be specific
4. **What it costs** — per query, per 1,000, per year at 10,000/day
5. **How fast it is** — p50/p95, broken down by stage
6. **What it is not safe for** — the honest limitations section
7. **What you would do next** — three things, ranked, with expected value

> **Section 6 is what distinguishes a professional report.** Every system has a
> boundary of safe use. **If you cannot state yours, you do not understand your
> own system.** Ours should not be relied on for a coverage decision without
> human review — and you should be able to say precisely why.

---

# 6 · Demo day — 5 minutes per pair

1. A question it answers well — 30 s
2. A question it **refuses**, and why refusal is correct — 30 s
3. `/metrics` — real cost, real latency — 1 min
4. **The regression gate failing** on a deliberate break — 1 min
5. **Your worst remaining failure**, and what you would do — 1 min
6. Questions — 1 min

> **Item 5 is graded.** Every system has one. A pair that claims otherwise has
> not looked.

---

## Deliverables checklist

- [ ] `service.py`, `ui.py`, `dashboard.py`, `gate.py`, `thresholds.yml`
- [ ] A green CI run, **and a screenshot of the red one** from D3
- [ ] The committed cache, so CI runs offline
- [ ] `report.md` — two pages, all seven sections, **including section 6**

## Targets

| Requirement | Target |
|---|---|
| `/ask`, `/health`, `/metrics` | working |
| Streaming TTFT | ≤ 1,500 ms |
| p95 cached / uncached | ≤ 800 ms / ≤ 6,000 ms |
| Cost per query | ≤ $0.01 |
| Regression gate | fails the build on a breach |

## If something goes wrong

| Symptom | Cause |
|---|---|
| The service is slow on every request | The pipeline is being built per request, not at startup |
| A model outage returns 500 | A3 — catch it and return 503 + `Retry-After` |
| Semantic cache returns wrong answers | That is B1. Find the threshold and **report it** |
| CI fails with a missing API key | It should run `AIP_OFFLINE=1`. Commit the cache |
| The gate never fires | Thresholds are too loose. D3 exists to catch exactly this |

## The sentence to leave with

> ### A gate you have not seen fail is a gate you do not have.
