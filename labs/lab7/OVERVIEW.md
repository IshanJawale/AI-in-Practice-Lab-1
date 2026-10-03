# Lab 7 — Ship It
### Note for students · read before the lab

> **In one line.** Six labs of components that nobody outside this room can
> use. Today it becomes a service with an SLO, a cost line, and a CI gate that
> fails the build when the answers get worse.

> **Working through the lab?** [`CONCEPTS.md`](CONCEPTS.md) is the reference to
> keep open beside your editor — every concept the lab uses, what it is, where
> it sits in the code, and where it came from in the theory.
---

## Why this lab exists

Every candidate has a RAG notebook. Almost none has a RAG **service** with a p95
latency budget and a continuous-integration gate on its own evaluation metrics.
That gap is the point of this lab, and it is why this deliverable is the one
that goes in your portfolio.

A notebook can be made to produce good numbers once. What it cannot do is keep
producing them under change, or state honestly where it stops working. The two
artefacts that prove you can do both are the **regression gate demonstrated
failing** and the **limitations section** of the evaluation report — and those
are also the two things the rubric weights most heavily outside the service
itself.

**Where it sits.** Last lab, and it integrates everything: Lab 3's retriever,
Labs 4–5's generation and fixes, Lab 6's guards. Demo day is in the last
twenty-five minutes of the session, live, on the projector.

---

## What you will build

- **`POST /ask`** returning an answer, citations, sources, latency, **cost and a
  trace id** — the last two in the response body, deliberately
- **Two cache layers**, and the measured cosine threshold at which the semantic
  one starts returning answers to the wrong question
- **Streaming**, and a defended answer to the problem it creates: you cannot
  validate citations until the answer is complete, and you have already sent it
- **Observability** — traces that answer *"why did request X take nine
  seconds?"*, a `/metrics` endpoint, and a dashboard
- **A regression gate**, wired into CI, running offline against your committed
  cache — and **demonstrated failing** on a deliberate break
- **A two-page evaluation report**, which is 16% of Module 1 on its own

---

## How to approach it

**This is an integration lab, and integration overruns.** The single best thing
you can do beforehand is make sure Labs 3–6 import cleanly from one place and
that you know which configuration you are shipping.

**Wire the guards in at the same time as the pipeline, not afterwards.** Nothing
goes red when they are missing — the service answers questions beautifully right
up until somebody edits a corpus document. Under deadline pressure the component
whose value is measured in things that did not happen is the one that gets cut.

**Leave twenty minutes for the report.** It is worth more per minute than
anything else in the lab, and section 6 — *what it is not safe for* — is the one
that distinguishes a professional document from a student one.

---

## Where this comes from in the theory

| Theory | What it claimed | Where you meet it today |
|---|---|---|
| **T1 §2.2** — latency | Output tokens are generated serially and dominate the wait | B4. Your stage breakdown will be ~98% generation |
| **T1 §2.3** — money | Cost per query, per 1,000, per year | `/metrics`, and section 4 of the report |
| **T1 §2.4** — reliability | Timeouts, retries, budgets, graceful degradation | A3. 422, 503 with `Retry-After`, 429 — never a 500 with a stack trace |
| **T1 §4** — architecture | The seven layers, of which the model is one | The service is that diagram, assembled |
| **T3 §5.3** — regression gates | Thresholds that fail the build | Part D, and D3 in particular |
| **T3 §3.2** — the triple | Quality *and* cost *and* latency | Why the gate has a cost threshold, not just quality ones |
| **T4 §6** — generation and citation | Grounding is only useful if it can be checked | A4 and B3 — the UI must show sources; streaming must not break validation |

---

## Hints

- **Return the trace id in the response.** When someone reports a bad answer
  from yesterday, that field is the difference between a lookup and an
  archaeology project.
- **The semantic cache is the feature most likely to silently break your
  system.** Below the safe threshold it returns a confident, well-cited, *fast*
  answer to a question nobody asked — and your latency and cost metrics both
  improve while correctness quietly falls. Sweep the threshold; the 0.95 in the
  starter is reasoned, not measured, and the comment says so.
- **A gate you have not seen fail is a gate you do not have.** Break something
  deliberately and show the red build. An eval that never runs, a threshold that
  is unreachable, and a swallowed exit code all produce the same green tick as a
  working gate.
- **Quote two p95 numbers, cached and uncached.** A blended figure moves when
  your traffic mix moves, and it lets a high hit rate hide a slow cold path.
- **The alert worth having is the refusal rate doubling.** A broken index throws
  no errors, raises no latency and costs no more — it just quietly stops finding
  things, and a well-built RAG system responds by declining.
- **Test your README on your partner's laptop, not yours.** Your machine has the
  venv, the keys, the warm cache and the file you forgot to commit.

---

## What separates a good report from an adequate one

- An adequate report lists metrics. A good one gives the **stage breakdown** of
  p95 and names the stage it would optimise first.
- An adequate limitations section is a disclaimer. A good one is a **boundary of
  safe use with the reason attached** — where the system may run unsupervised
  and where it may not, and precisely why.
- **Section 1 must be readable by a non-engineer.** The people who decide whether
  this gets deployed are not going to read your metric table.

---

## Questions we will discuss

1. Your worst remaining failure — demo item 5, and the one item that cannot be
   rehearsed by picking a favourable question. What is it, and what would you do?
2. Where did you set the semantic cache threshold, and what did the wrong answers
   look like just below it?
3. Your gate has a cost ceiling as well as quality floors. Which change would
   have passed the quality gate and been caught by the cost one?
4. Looking back across all seven labs: which measurement surprised you most, and
   what would you have shipped if you had never taken it?
