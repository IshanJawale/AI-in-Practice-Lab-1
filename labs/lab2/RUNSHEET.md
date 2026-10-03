# Lab 2 — Runsheet

**Follow this top to bottom.** Every step says *why* it exists, *what* to do,
*how* to do it, and how you know you are finished.

Three documents, three jobs:

| | |
|---|---|
| [`OVERVIEW.md`](OVERVIEW.md) | **why** — read before the lab |
| [`README.md`](README.md) | **the brief** — targets, deliverables, rubric |
| [`CONCEPTS.md`](CONCEPTS.md) | **the reference** — concept → code → theory. Keep it open too |
| this file | **the actions** — follow it top to bottom during the lab |

**Keep a scratch file open from the start.** Many steps say *write this down*.
Those notes are your report.

---

## The lab in one line

> You have one configuration and an opinion. By 3pm you will have seven
> configurations, a table, and a recommendation you can defend.

---

## Before you sit down

- [ ] `make check` → `Environment is ready for Labs 1 and 2.`
- [ ] Lab 1 still runs: `python labs/lab1/run_eval.py --split dev --variant c --n 5`
- [ ] `python labs/lab2/stats.py` runs, and you understand the output
- [ ] `OVERVIEW.md` read
- [ ] `CONCEPTS.md` skimmed — especially *The statistics*, before Part D
- [ ] `aip/evals.py` skimmed

**Lab 2 imports your Lab 1 code.** A broken Lab 1 is a broken Lab 2. If that
second checkbox fails, fix it before anything else.

---

# 0 · Setup — 10 min

**Why.** You are about to quote numbers from a measuring instrument. You should
know how it works before you trust it.

**0.1** Open three things and leave them open:

| | |
|---|---|
| edit | `labs/lab2/variants.py` |
| read | `aip/evals.py` |
| scratch | a notes file for the report |

**0.2** Read `aip/evals.py`. **All of it.** Find these four things and note the
line numbers:

- where `field_accuracy` differs from record accuracy
- what `run_eval` records besides the score
- what `wilson_interval` protects you from
- what `paired_test` counts

> **Done when:** you can say what the harness measures without opening it again.

> 💡 **Theory.** T3 §1 — *"you cannot see whether a stochastic system got
> better."* This file is the instrument that lets you see.

---

# 1 · Part A — few-shot selection — 40 min

**Why.** "Show, don't tell" is the oldest advice in prompting. But examples are
not free: they are pasted into **every single call, forever**. So the question
is not *"do examples help?"* — it is *"do they earn their tokens?"*

**1.1 — `TODO A1`. Choose 6 examples by hand.**

**Do not pick typical tickets.** A typical ticket teaches the model nothing it
did not already know. Pick the edges:

- the `billing` / `complaint` boundary
- one with **no** policy number (teaches `null`)
- a Hinglish one
- a satisfied-but-urgent one (the sentiment/urgency trap)
- one whose policy number is only in a quoted reply
- **one you got wrong in Lab 1**

Write **one line per example: what does this teach that prose cannot?**
If you cannot answer that, it is the wrong example.

> 💡 **Theory.** T2 §2.2 — *choose the edges, not the average.*

**1.2 — `TODO A2`. Render them into the prompt.**

The example output format must be **byte-identical** to the format you are
asking the model to produce. A mismatch here is a classic own goal: you show it
one shape and ask for another, then wonder why parsing broke.

**1.3** Run the comparison:

```bash
python labs/lab2/grid.py --variants zero_shot few_shot --split dev
```

**1.4 — `TODO A4`. The question that matters.**

Your 6 examples came **out of** the dev set. You are now measuring **on** the
dev set. Name that problem in one sentence. Then fix it, and write down what you
did — there is more than one defensible fix.

> 💡 **Theory.** T3 §2.4 — dev/test discipline. Selecting on the same data you
> measure on inflates the result. Every real team does this by accident at least
> once.

> **Done when:** you have both numbers, and a written answer to 1.4.
>
> ⚠️ **Prepare to be annoyed.** Few-shot may buy you **nothing.** The reference
> moved 0.928 → 0.931 on field accuracy, moved record accuracy *down*, and the
> paired test returned **p = 1.00**.
>
> The reason is the lesson: your zero-shot prompt already carries the labelling
> rules, inside the Pydantic field descriptions — exactly where T2 §3.2 told you
> to put them. **The examples had nothing left to teach.**
>
> And if few-shot gives you +20 points, that is *not* a win. It means your
> zero-shot prompt was under-specified. Fix that instead of banking the number.

---

# 2 · Part B — run the grid — 40 min

**Why.** One configuration is an anecdote. Seven is a dataset. You cannot
recommend anything until you have seen the alternatives side by side.

**2.1 — `TODO B`. Implement the remaining variants.**

`zero_shot`, `few_shot`, `few_shot_reasoned`, and their `_main` versions.

For `TicketRecordReasoned`, put `reasoning` **first**.

> 💡 **Theory.** T2 §3.3. The model is autoregressive — it is conditioned by
> what it has already written. Reasoning first *shapes* the answer. Reasoning
> last is a **post-hoc rationalisation** of an answer already chosen. Same
> fields, different mechanism, different accuracy.

**2.2** Run everything:

```bash
python labs/lab2/grid.py --all --split dev --save reports/lab2_grid.json
```

This takes a few minutes. **Start it, then keep reading `aip/evals.py`.**

**2.3** Build one table. One row per configuration:

```
record_accuracy | field_accuracy | schema_valid | repair_rate |
cost_usd | cost_per_1k_tickets | p50_ms | p95_ms
```

**2.4** Answer in your notes:

1. **Which knob moved the numbers more — the prompt, or the model tier?**
   Most people guess wrong.
2. **What did the reasoning field cost in output tokens, and what did it buy?**
   Express it as *accuracy points per rupee*.
3. **Is any configuration worse than another on _every_ axis?** That is a
   **dominated** configuration — there is never a reason to pick it. The harness
   prints these for you. Naming them is a real finding.

> **Done when:** the table is complete and all three questions are answered.

> 💡 **Theory.** T1 §2 — the four resources. Every row of your table is a
> different trade between tokens, money, latency and attention. And T3 §5.2 —
> *change one thing*: if you move the prompt **and** the tier between two runs,
> the delta is uninterpretable and you paid for nothing.

---

# 3 · Part C — the cascade — 30 min

**Why.** Most tickets are easy. A few are hard. Paying large-model prices on
*every* ticket to handle the hard 10% is waste. So: try cheap first, escalate
only when you have reason to doubt.

**3.1 — `TODO C`. Implement `cascade()`.**

```
   SMALL model
       │
       ├── looks confident ──▶ accept
       │
       └── looks doubtful ──▶ MAIN model ──▶ accept
```

Pick a trigger for "looks doubtful", weakest to strongest:

| Trigger | Cost | Works? |
|---|---|---|
| validation failed | free | weak — misses confident errors |
| `evidence` empty or very short | free | surprisingly decent |
| `urgency >= 4` | free | not a confidence signal at all |
| two SMALL samples disagree | 2× small | best of the four |

Set `rec['_path'] = 'small' | 'large'` so the harness can report escalation.

> 💡 **Theory.** T2 §4.3 — *do not ask the model for its confidence.* Stated
> confidence is generated text, not a probability. Your trigger must be
> **behavioural** — something you observed it do.

**3.2** Report three numbers: **escalation rate**, **blended cost**, **blended
accuracy** — each compared against both pure configurations.

> ⚠️ **The silent bug you will hit.** The obvious way to detect disagreement is
> to call the model twice at temperature 0. Those are **the same request**, so
> the cache serves the second from the first. The answers are byte-identical.
> Disagreement is never detected. Escalation reads **0%**. Your cascade reports
> the small model's accuracy at the small model's price and looks like it works.
>
> **Nothing errors.** The only symptom is `escalated 0.00`.
>
> Fix: draw the second sample at **temperature > 0**. That changes the sampling
> *and* the cache key.

**3.3 — Then interrogate the trigger.**

Measure how often your two samples agree **when the answer is right** versus
**when it is wrong**. If those two rates are close, disagreement tells you
nothing.

> The reference measured **94% agreement when correct vs 83% when wrong** —
> which caught **2 of 12** errors and produced a cascade worth almost nothing.
>
> Why: self-consistency detects **variance**. What this model has is **bias**.
> It is not unsure — it is *consistently wrong*.
>
> **Reporting that, with the numbers, is full marks.** A cascade you did not
> interrogate is not.

> **Done when:** escalation is **non-zero**, and you have the agree-when-right
> vs agree-when-wrong numbers.

---

# 4 · Part D — is your difference real? — 20 min

**Why.** This is the core of the lab, and the skill you will use for the rest of
your career. Everything before this produced numbers. This decides which of them
mean anything.

**4.1 — Confidence intervals.**

Your measured accuracy is an **estimate**, not the truth. The interval says how
far the truth could plausibly sit from it.

```bash
python labs/lab2/stats.py
```

At n = 60 and p = 0.90 the half-width is about **±0.076**. So 0.88 and 0.91 have
intervals that overlap almost entirely.

Compute the Wilson interval for your best two configurations.

> ⚠️ **Read the overlap correctly — it is asymmetric.**
> - Intervals **do not** overlap → the difference is real.
> - Intervals **do** overlap → **you have learned nothing.** It does *not* mean
>   "no difference."
>
> Comparing two intervals is a conservative test. That gap is exactly why 4.2
> exists.

**4.2 — The paired test.**

Both configurations saw the **same 60 tickets**. So throw away every ticket they
agree on and count only the disagreements:

- **b** = A right, B wrong
- **c** = B right, A wrong

`paired_test()` in `stats.py` does it.

**Why pairing wins:** the biggest source of noise is that *some tickets are just
harder than others*. Comparing two overall percentages makes you fight that
noise. Comparing the same tickets **cancels it exactly**.

To feel the difference: at n=60, b=4/c=10 gives **p = 0.18** — nothing. But
b=2/c=14 gives **p = 0.004**. Same sixty items. Real conclusion.

**4.3** Write down: **b, c, the p-value, and your conclusion.**

> **"No significant difference" is a perfectly good result.** It means: choose
> on cost.

> 💡 **Theory.** T3 §2.5 — *Is the difference real?* — and the interactive
> slide with the sliders. `labs/lab2/CONCEPTS.md` has the same material in a
> form you can consult mid-lab.

> **Done when:** every comparison you intend to claim has a p-value behind it.

---

# 5 · Part E — error analysis and recommendation — 25 min

**Why.** An average tells you *how much* is wrong. It never tells you *what* is
wrong. Only reading failures does that.

> 💡 **Theory.** T3 §5.1 — *error analysis is the step that is actually worth
> your time.*

**5.1** Take your best configuration. **Read 20 failures.** Actually read them.

**5.2** Group them. Name the top three groups with counts.

**5.3** For your worst field, build the confusion matrix. There is a specific
systematic confusion in this dataset that aggregate accuracy hides. Find it.

**5.4 — Write the recommendation. One paragraph.** It must contain:

- [ ] a named configuration
- [ ] the three numbers (quality, cost, latency)
- [ ] the annual cost at 10,000 tickets/day
- [ ] **one condition that would change your mind**

> 📌 **Calibration.** On test, the reference measured:
>
> | | field | cost | p95 |
> |---|---|---|---|
> | `SMALL` zero-shot | 0.930 | **$0.080** | 2,276 ms |
> | `MAIN` zero-shot | 0.942 | $0.382 | 6,720 ms |
>
> **4.8× the cost and 3× the latency, for a difference the paired test could not
> distinguish from noise (p = 0.71).**
>
> *"The expensive configuration is not detectably better, therefore ship the
> cheap one"* is a **complete and correct** recommendation.

> **Done when:** the paragraph is written and every checkbox above is ticked.

---

# 6 · Show & tell — 4 minutes each

1. Your grid table, on screen — 1 min
2. Your recommendation, and the number behind it — 1 min
3. **Your negative result** — 1 min
4. Questions — 1 min

---

## Deliverables checklist

- [ ] `labs/lab2/variants.py` — your configurations, including the cascade
- [ ] `reports/lab2_grid.json`
- [ ] `report.md`, at most three pages:
  - [ ] the grid table
  - [ ] few-shot selection justification + your answer to A4
  - [ ] cascade: escalation rate, blended cost, blended accuracy
  - [ ] the paired test: **b, c, p**
  - [ ] three error clusters + the confusion matrix
  - [ ] the recommendation paragraph
  - [ ] **at least one negative result**

> There is **no accuracy target in this lab.** You are graded on the quality of
> your decision and the evidence behind it. When the reference ran this grid, the
> honest answer was *"nothing beat the cheap baseline detectably, so ship the
> cheap one."* Reaching that, with the tests to support it, is full marks.
> Inventing an improvement is not.

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| `NotImplementedError` | A `TODO` is unfinished. The harness names the variant. |
| `ImportError` from `labs.lab1.extract` | Lab 1 is broken. Fix it first. |
| `escalated 0.00` | The cache trap. See 3.2. |
| `cost` says `UNPRICED` | You are on `AIP_PROFILE=nvidia`. Compare on **tokens** — cost is proportional to them. |
| The grid is slow | Normal. 7 configurations × 60 tickets. The **re-run** is nearly free. |

**On Gemini if you can** — every number quoted here was measured on it. NVIDIA
works but is 7–10× slower; use `--n 20`.

**Stuck for more than ten minutes? Ask.**

---

## The sentence to leave with

> ### No number, no claim.
