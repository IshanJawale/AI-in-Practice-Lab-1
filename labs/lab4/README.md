# Lab 4 — RAG v1: Grounded Answers with Citations
**3 hours · Pairs · Prepared by T4**

> **Read [`OVERVIEW.md`](OVERVIEW.md) first** — why this lab exists, how to
> approach the three hours, the hints, and the map back to the theory
> sessions. Keep [`CONCEPTS.md`](CONCEPTS.md) open while you work.
> This file is the detail.

---

## The problem

Lab 3 gave you a retriever that puts the right document in the top 5 about 85%
of the time. Agents still have to read the passages and work out the answer.

Now generate the answer. But an insurance helpdesk cannot ship a system that
sometimes invents a claim deadline, so the answer comes with two hard
constraints:

1. **Every factual sentence carries a citation** to a source you supplied, and
   the citation index is validated in code.
2. **When the sources do not contain the answer, the system says so** — in an
   exact, machine-detectable form — rather than guessing.

Constraint 2 is where systems like this usually fail, and it is why 5 of the 45
golden questions are unanswerable.

### Targets on the 45-question golden set

| Metric | Target | Reference solution |
|---|---|---|
| Citation validity (every `[n]` refers to a real source) | **1.00** | 1.000 |
| Faithfulness (no claim unsupported by context) | ≥ 0.90 | 0.933 |
| Answer correctness (LLM-judged, calibrated) | ≥ 0.75 | 0.825 |
| Refusal recall (of 5 unanswerable, how many declined) | ≥ 4/5 | 5/5 |
| Refusal precision (of your declines, how many were right) | ≥ 0.70 | 0.714 |
| Repair rate | reported | 0.089 |
| Cost per query | ≤ $0.01 | $0.0095 |
| p95 end-to-end latency | ≤ 6,000 ms | 4,259 ms |

**Both refusal numbers are extremely noisy and you must say so.** There are only
5 unanswerable questions, and the reference solution declined 7 questions in
total. One case moves precision by 0.12 and recall by 0.20. Report the raw
counts alongside the ratios, and do not claim a difference of less than about
0.15 on either. This is T3 §2.1 in miniature: a metric computed over 5 items is
a direction, not a measurement.

Note that refusal precision and recall are both listed. A system that refuses
everything gets recall 1.00 and is useless. **Reporting only one of these is
the classic way to make a bad system look good, and it will cost you marks.**

---

## Timetable

| Time | Part | What you do |
|---|---|---|
| 0:00–0:20 | **A** | The generation prompt and the output contract |
| 0:20–0:50 | **B** | Citation enforcement in code |
| 0:50–1:20 | **C** | Refusal: the escape hatch, and measuring both directions |
| 1:20–2:05 | **D** | The judge: rubric, calibration, and earning the right to use it |
| 2:05–2:40 | **E** | Full evaluation + the gold-context decomposition |
| 2:40–3:00 | Show & tell | Your numbers, and one answer that is confidently wrong |

---

## Part A — The generation prompt (20 min)

Open `labs/lab4/rag.py`. Write `ANSWER_SYSTEM` yourself before looking at
`aip/rag.py::ANSWER_SYSTEM`. Then compare and note the differences.

Required elements (T4 §6.1):

1. Answer **only** from the numbered sources. Explicitly forbid general knowledge.
2. Cite by index: `[1]`, `[2][5]`.
3. Never cite a number that was not supplied.
4. An exact refusal string, given verbatim in the prompt.
5. What to do when sources disagree — surface it, do not pick silently.
6. Length discipline. Two or three sentences unless the question needs more.

Rule 6 is not cosmetic: output tokens dominate both latency and cost (T1 §2.2).

---

## Part B — Citation enforcement (30 min)

**B1.** Number the sources in the context block. `aip.retrieval.format_context`
does this. Read it and understand why numbering makes hallucination detectable:
the model can only cite a number you gave it, so `[7]` with five sources is a
*provable* error found by three lines of regex.

**B2.** Implement `validate_answer()`. It must check:
- every `[n]` is in range → otherwise reject
- the answer is non-empty and not truncated (`finish_reason == "length"`)
- if not a refusal, at least one citation is present

**B3.** Decide what happens on failure, and defend the choice:
- retry with a corrective message?
- strip invalid citations and return?
- fall back to refusal?

There is no single right answer, but a system that silently returns an answer
with a bogus citation is definitely wrong. Say which you chose and why.

**B4.** Report citation validity across all 45 questions. **The target is 1.00**,
and it is achievable, because this is a code guarantee and not a model
behaviour.

---

## Part C — Refusal (30 min)

**C1.** Run the 5 unanswerable questions (Q36–Q40). Count refusals.

**C2.** Q37 is the interesting one: *"Does Aurora cover treatment in Singapore,
and up to what limit?"* The corpus confirms that a Platinum international
benefit exists but the addendum describing it is absent.

The right behaviour is a **partial** answer: state what is supported, and
refuse the part that is not. Does your system do that? Most do not on the first
attempt. Make it, and describe what you changed.

**C3.** Now measure the other direction. Run all 40 answerable questions and
count how many were refused. Compute:

```
refusal recall    = refused_and_should_have  / should_have_refused
refusal precision = refused_and_should_have  / total_refused
```

**C4.** Move the dial. Make the refusal instruction stricter, re-run, and
report how both numbers moved. Plot the trade-off if you have time.

Then state, as a product decision with a reason: **where would you set it for
an insurance helpdesk, and why?** "Higher precision" is not a reason; a claim
about the relative cost of the two error types is.

---

## Part D — The judge (45 min)

**D1.** Write two separate single-criterion judge rubrics (T3 §4.2):
- **faithfulness** — is every claim supported by the supplied context?
- **correctness** — does the answer match the gold answer substantively?

`aip.evals` has starting templates. Improve them; they are deliberately
improvable.

**D2 — calibration, and this is required.** Hand-label 20 answers yourself
against each rubric, *before* looking at what the judge said. Then compute
Cohen's kappa with `aip.evals.judge_agreement`.

**Report κ. If κ < 0.4, fix the rubric and re-run.** You may not report a judge
number in this lab without its κ. The fix is almost always the rubric, not the
model — read your disagreements and you will usually find that your own
labelling rule was implicit.

> **A war story, because it will happen to you.** The reference solution first
> measured faithfulness at **0.667** and shipped nothing, because the number
> looked plausible for a first attempt. It was wrong. `llm_judge` capped output
> at 512 tokens; the judge tier is a reasoning model that spent most of that
> budget on invisible thinking, so the JSON verdict was **truncated
> mid-object**, failed to parse, and was scored 0. The true faithfulness was
> **0.933**.
>
> Three things let it be caught, and all three are cheap:
> 1. **An internal contradiction.** 8 of the 15 "unfaithful" answers were
>    simultaneously judged *fully correct*. Two metrics disagreeing about the
>    same answer is a signal that one of them is broken.
> 2. **A deterministic cross-check.** Every number in 14 of the 15 "unfaithful"
>    answers was present in the corpus. A free check contradicting an expensive
>    one should always win your attention first.
> 3. **Reading the judge's raw output**, which said, verbatim,
>    ``` ```json\n{"score": 1, "unsupported_ ```
>
> The general rule: **a parse failure is missing data, not a failing answer.**
> Scoring it 0 puts a silent, systematic, downward bias on your headline metric.
> `aip.evals.llm_judge` now retries once at double the token budget and returns
> `parse_error` so callers can exclude the case; `_score()` in the reference
> returns `None` rather than 0. Check how your own harness treats judge
> failures before you trust any number it produces.

**D3.** Note the self-preference problem (T3 §4.1). If your judge is the same
model that generated the answer, say so and explain the direction of the bias.
Use a different tier or a different provider profile if you can.

---

## Part E — Full evaluation and the decomposition (35 min)

```bash
python labs/lab4/evaluate.py --full --save reports/lab4.json
```

**E1.** Report every metric in the target table.

**E2 — the most useful experiment in RAG (T4 §5, failure 6).** Run the
generator twice on the answerable questions:

- with **retrieved** context (your real system)
- with **gold** context — the actual relevant documents, chunked, no retrieval

```bash
python labs/lab4/evaluate.py --gold-context
```

The gap between those two correctness numbers is exactly the damage your
retriever is doing. Report:

```
correctness with gold context     = A     ← the generation ceiling
correctness with retrieved context = B     ← your system
retrieval-attributable loss        = A − B
generation-attributable loss       = 1 − A
```

**This decomposition tells you where to spend Lab 5.** If A is 0.95 and B is
0.72, work on retrieval. If A is 0.78, no retrieval improvement will save you
and your generation prompt is the problem.

**E3.** Read 10 wrong answers. For each, note which of the seven failure modes
applies. This is your Lab 5 backlog — bring it with you.

---

## Deliverables

1. `labs/lab4/rag.py`, `labs/lab4/evaluate.py`
2. `report.md` — at most three pages:
   - your `ANSWER_SYSTEM`, with the differences from the reference noted
   - citation validity, and what you do on failure
   - the refusal precision/recall table at two strictness settings, with your
     product recommendation
   - judge κ for both rubrics, and how you fixed the rubric if you had to
   - the E2 decomposition table with A, B, and the two attributed losses
   - the E3 failure-mode tally
3. `reports/lab4.json`

---

## Rubric (9% of Module 1)

| Criterion | Weight | Full marks means |
|---|---|---|
| Grounding | 20% | Citation validity 1.00, enforced in code not by prompt |
| Refusal | 20% | Both directions measured; Q37 partial handled; product recommendation defended |
| Judge rigour | 25% | κ reported for both rubrics, ≥ 0.4, self-preference addressed |
| Decomposition | 20% | E2 done correctly and the conclusion drawn |
| Engineering | 15% | Runs on the full set within budget; traces usable in Lab 5 |

---

## Stretch

1. **Streaming.** Stream the answer token-by-token. Measure TTFT vs total.
   Then explain the problem streaming creates for citation validation, and
   solve it.
2. **Answer-level confidence.** Combine top retrieval score, number of sources
   cited, and self-consistency across 3 samples into a single confidence score.
   Does it predict correctness? Show the correlation, not a claim.
3. **Two-model agreement.** Generate with two providers; disagreement flags for
   review. What is the false-alarm rate?
4. **Conversational RAG.** Add history and a query-rewriting step that resolves
   "what about on Gold?" against the previous turn. Measure the rewriter's
   accuracy separately.
