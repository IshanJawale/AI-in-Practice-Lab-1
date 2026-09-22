# Lab 4 — Runsheet

**Follow this top to bottom.** Every step says *why* it exists, *what* to do,
*how* to do it, and how you know you are finished.

| | |
|---|---|
| [`OVERVIEW.md`](OVERVIEW.md) | **why** — read before the lab |
| [`README.md`](README.md) | **the brief** — targets, deliverables, rubric |
| [`CONCEPTS.md`](CONCEPTS.md) | **the reference** — concept → code → theory |
| [`CODE_GUIDE.md`](CODE_GUIDE.md) | **the files** — what is provided, every TODO itemised |
| this file | **the actions** — follow it during the lab |

**Pairs.** Swap driver at each part.

---

## The lab in one line

> Lab 3 found the right passage. Now write the answer — with a citation on
> every claim, and an honest refusal when the sources do not contain one.

---

## Before you sit down

- [ ] Lab 3 finished; you know your winning retrieval configuration
- [ ] `make check` clean
- [ ] `OVERVIEW.md` read; T4 §6 (generation, citation, refusal) and T3 §4
      (LLM-as-judge) skimmed

---

# 0 · Setup — 10 min

Open `labs/lab4/rag.py`, `labs/lab4/evaluate.py`, and a scratch file.

**Put your Lab 3 configuration into `build_retriever()`** in `evaluate.py`. The
placeholder there is not your answer — using it throws away Lab 3.

> **Done when:** `build_retriever()` reflects your own chunking, retriever and
> `final_k`.

---

# 1 · Part A — the answer prompt — 20 min

**Why.** The output contract is what makes everything downstream checkable.

**1.1** Write `ANSWER_SYSTEM` **yourself, before opening `aip/rag.py`.** Six
required elements (T4 §6.1):

1. Answer **only** from the numbered sources; forbid general knowledge
2. Cite by index — `[1]`, `[2][5]`
3. Never cite a number that was not supplied
4. An exact refusal string, given verbatim
5. What to do when sources disagree — surface it, never pick silently
6. Length discipline — two or three sentences unless more is needed

**1.2** *Then* read `aip/rag.py::ANSWER_SYSTEM` and note every difference.

> Rule 6 is not cosmetic. Output tokens dominate latency and cost (T1 §2.2).

---

# 2 · Part B — citation enforcement — 30 min

**Why.** A citation the model invented is indistinguishable from a real one —
unless you number the sources. Then `[7]` with five sources is a *provable*
error found by three lines of regex.

**2.1** Read `aip.retrieval.format_context`. Understand why numbering makes
hallucination detectable.

**2.2 — `B2`.** Implement `validate_answer()`. It must check:
- every `[n]` is in range
- the answer is non-empty and **not truncated** (`finish_reason == "length"`)
- if it is not a refusal, at least one citation is present

**2.3 — `B3`.** Decide what happens on failure — retry with a corrective
message, strip the bad citation, or fall back to refusal — and **defend it.**
There is no single right answer. There is one wrong one: silently returning an
answer with a bogus citation.

**2.4 — `B4`.** Report citation validity across all 45.

> **Checkpoint. The target is 1.00 and it is achievable**, because this is a
> **code guarantee, not a model behaviour.** If yours is below 1.00, your
> validator is not wired into the return path.

---

# 3 · Part C — refusal, both directions — 30 min

**Why.** A system that never refuses invents deadlines. A system that always
refuses is useless. You must measure both.

**3.1 — `C1`.** Run Q36–Q40, the five unanswerable ones. Count refusals.

**3.2 — `C2`. Q37 is the interesting one.** *"Does Aurora cover treatment in
Singapore, and up to what limit?"* The corpus confirms a Platinum international
benefit exists, but the addendum describing it is missing.

The right behaviour is a **partial** answer: state what is supported, refuse
the rest. **Most systems do not do this on the first attempt.** Make yours, and
say what you changed.

**3.3 — `C3`.** Run all 40 answerable questions and count wrongful refusals:

```
refusal recall    = refused_and_should_have / should_have_refused
refusal precision = refused_and_should_have / total_refused
```

**3.4 — `C4`.** Make the refusal instruction stricter, re-run, report how both
numbers moved. Then state, **as a product decision with a reason**, where you
would set it for an insurance helpdesk. *"Higher precision"* is not a reason; a
claim about the relative cost of the two error types is.

> ⚠️ **Both refusal numbers are extremely noisy, and you must say so.** Five
> unanswerable questions; the reference declined seven in total. **One case
> moves precision by 0.12 and recall by 0.20.** Report raw counts beside the
> ratios and claim no difference below ~0.15. T3 §2.1 in miniature.
>
> And report **both**. A system that refuses everything scores recall 1.00.
> Reporting only one is the classic way to make a bad system look good, and it
> costs marks.

---

# 4 · Part D — the judge — 45 min

**Why.** You are about to measure quality with a model. Before you may quote
its numbers, you have to show it agrees with you.

**4.1 — `D1`.** Write **two separate single-criterion** rubrics (T3 §4.2):
**faithfulness** (is every claim supported by the context?) and **correctness**
(does it match the gold answer substantively?).

> Never one judge weighing several things. A single number from a
> multi-criterion judge cannot be recovered into its parts.

`aip.evals` has templates. They are **deliberately improvable**.

**4.2 — `D2`. Calibration. This is required.**

```bash
python labs/lab4/evaluate.py --calibrate     # writes the sheet
python labs/lab4/evaluate.py --kappa         # after you have labelled
```

Hand-label **20** answers against each rubric **before** looking at the judge.
Then compute Cohen's κ.

> **Report κ. If κ < 0.4, fix the rubric and re-run.** You may not report a
> judge number in this lab without its κ. The fix is almost always **the
> rubric**, not the model — read your disagreements and you will find your own
> labelling rule was implicit.

**4.3 — `D3`.** If your judge is the same model that generated the answer, say
so and state the **direction** of the bias (T3 §4.1). Use a different tier or
profile if you can.

> 📌 **The war story, because it will happen to you.** The reference first
> measured faithfulness **0.667**. It was wrong — the true value was **0.933**.
> `llm_judge` capped output at 512 tokens; the judge is a reasoning model that
> spent most of that on invisible thinking, so the JSON was truncated
> mid-object, failed to parse, and was scored **0**.
>
> Three cheap things caught it: an **internal contradiction** (8 of 15
> "unfaithful" answers were judged fully correct); a **deterministic
> cross-check** (every number in 14 of 15 was present in the corpus); and
> **reading the judge's raw output.**
>
> The rule: **a parse failure is missing data, not a failing answer.** Check
> how your harness treats judge failures before you trust any number it prints.

---

# 5 · Part E — full evaluation and the decomposition — 35 min

**5.1 — `E1`.**

```bash
python labs/lab4/evaluate.py --full --save reports/lab4.json
```

Report every metric in the target table.

**5.2 — `E2`. The most useful experiment in RAG** (T4 §5, failure 6).

```bash
python labs/lab4/evaluate.py --gold-context
```

```
correctness with gold context      = A    ← the generation ceiling
correctness with retrieved context = B    ← your system
retrieval-attributable loss        = A − B
generation-attributable loss       = 1 − A
```

> **This decomposition tells you where to spend Lab 5.** If A is 0.95 and B is
> 0.72, work on retrieval. If A is 0.78, no retrieval improvement will save you.

**5.3 — `E3`.** Read **10 wrong answers**. Tag each with one of the seven
failure modes. **This is your Lab 5 backlog — bring it with you.**

> **Done when:** `reports/lab4.json` exists. Lab 5 reads it.

---

## Deliverables checklist

- [ ] `labs/lab4/rag.py`, `labs/lab4/evaluate.py`
- [ ] `reports/lab4.json`
- [ ] `report.md` ≤ 3 pages:
  - [ ] your `ANSWER_SYSTEM` + differences from the reference
  - [ ] citation validity, and what you do on failure
  - [ ] refusal precision/recall **at two strictness settings**, with raw counts
  - [ ] **κ for both rubrics**, and how you fixed the rubric
  - [ ] the E2 decomposition: A, B, and both attributed losses
  - [ ] the E3 failure-mode tally

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| Citation validity < 1.00 | The validator is not on the return path |
| Judge scores suspiciously low | Truncation. Check `finish_reason` and `parse_error` |
| κ below 0.4 | The rubric, not the model. Read your disagreements |
| Refusal numbers swing wildly | n = 5. They are noisy. Report counts |
| `--gold-context` errors | Q36/Q38/Q39 have no gold docs; skip them |

## The sentence to leave with

> ### A parse failure is missing data, not a failing answer.
