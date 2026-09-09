# Lab 2 in plain language — what you are doing, and why

*Read this before `README.md`. It is the map; the README is the terrain.*

---

## The one-sentence version

**In Lab 1 you built something that works. In Lab 2 you find out whether it is
the best version of itself — and you build the measuring instrument that can
answer that question honestly.**

---

## Why this lab exists

You finished Lab 1 with an extractor and an opinion. Maybe your opinion is
*"the long field descriptions did the heavy lifting"* or *"the bigger model
would obviously be better."*

Here is the uncomfortable part: **you have no evidence for any of it.** You
tried one configuration. There are at least twelve reasonable ones.

Now imagine your manager asks: *"Should we deploy this? Which version? What
will it cost us per year?"*

"This one felt good" is not an answer anyone can act on. Lab 2 is about being
able to answer that question with a table.

### The trap this lab is built to spring

Language models are **stochastic** — run the same thing twice and you can get
different answers. That makes "did it get better?" genuinely hard to see.

Suppose configuration A gets 88% and configuration B gets 91%. B is better,
right?

**No.** On 60 test cases, that difference is well inside the noise. If you
re-ran both, B might come out lower. Shipping B because of that 3 points is a
decision made on nothing at all — and people do it constantly, in real
companies, with real money.

This lab teaches you to tell the difference between *a result* and *a wobble*.

---

## The scope, in four pictures

### 1 · You have a grid of choices

| Knob | Settings you will try |
|---|---|
| **How you prompt** | zero-shot · few-shot (6 examples) · few-shot + reasoning field |
| **Which model** | `SMALL` (cheap, fast) · `MAIN` (expensive, slow) |
| **How you route** | one call every time · cheap-first, escalate when unsure |

Three prompt styles × two models = six combinations, plus the cascade = **seven
configurations**. You will run every one of them on the same 60 tickets.

### 2 · You measure three things, not one

Never quality alone. Always:

```
        quality  ×  cost  ×  latency
```

A configuration that is 1% more accurate and 5× more expensive is usually a bad
trade. You cannot see that trade-off unless you measure all three, and the
whole point of the harness is that it measures all three for free.

### 3 · You check whether your differences are real

For every comparison you want to make, you run a **statistical test**. If the
test says "no significant difference", that is a *result* — it tells you to
**choose on cost instead**.

### 4 · You write a recommendation someone could act on

One paragraph. Names a configuration. Gives the three numbers. States the
annual cost. And states **one thing that would change your mind.**

---

## The steps: why, what, how

### Part A — Few-shot selection (40 min)

**Why.** "Show, don't tell" is the oldest advice in prompting. Sometimes an
example teaches something a paragraph of rules cannot. But examples cost tokens
on *every single call*, forever — so you need to know whether they earn it.

**What.** Pick 6 example tickets, put them in the prompt, and measure whether
accuracy improves.

**How.**
1. Choose 6 tickets from the dev set **by hand**.
2. **Pick edge cases, not typical ones.** A boring ticket teaches the model
   nothing it did not already know. Pick the billing/complaint boundary, one
   with no policy number, a Hinglish one, one you got wrong in Lab 1.
3. Write one line per example: *what does this teach that prose cannot?* If you
   cannot answer, it is the wrong example.
4. Render them into the prompt in **exactly** the output format you are asking
   for. A format mismatch here is a classic own goal.
5. Run and compare:
   ```bash
   python labs/lab2/grid.py --variants zero_shot few_shot --split dev
   ```

**The trap (A4).** You picked your 6 examples *from the dev set*, and now you
are measuring *on the dev set*. Your model has effectively seen the answers.
Name that problem and fix it. There is more than one defensible fix — pick one
and say what you did.

> **Prepare to be annoyed.** Few-shot may buy you **nothing**. When the
> reference solution ran this, accuracy moved 0.928 → 0.931 and record accuracy
> went *down*, p = 1.00.
>
> The reason is the lesson: your zero-shot prompt already contains the labelling
> rules, inside the Pydantic field descriptions — which is exactly where T2 §3.2
> told you to put them. **The examples had nothing left to teach.**
>
> And if few-shot *does* buy you 20 points, that is not a victory. It means your
> zero-shot prompt was under-specified. Go fix that instead.

### Part B — Run the grid (40 min)

**Why.** One configuration is an anecdote. Seven is a dataset.

**What.** Run every configuration, put them in one table, read it.

**How.**
```bash
python labs/lab2/grid.py --all --split dev --save reports/lab2_grid.json
```

Then answer three questions in your report:

1. **Which knob mattered more — the prompt, or the model?** (Most people guess
   wrong.)
2. **What did the reasoning field cost in output tokens, and what did it buy?**
   Express it as accuracy points per rupee.
3. **Is any configuration worse than another on *every* axis?** That is called a
   **dominated** configuration — there is never a reason to pick it. Saying so
   explicitly is a real finding, and the harness computes it for you.

### Part C — The cascade (30 min)

**Why.** Most tickets are easy. A few are hard. Paying large-model prices on
every ticket to handle the hard 10% is wasteful. So: try cheap first, and
escalate only when you have reason to doubt the answer.

**What.**

```
   SMALL model
       │
       ├── looks confident ────────▶ accept
       │
       └── looks doubtful ─────────▶ MAIN model ──▶ accept
```

**How.** Pick a trigger for "looks doubtful". Options, weakest to strongest:
validation failed · evidence field is empty · run it twice and see if the two
answers disagree.

Then report **escalation rate**, **blended cost**, **blended accuracy**.

> **The silent bug you will hit — and it is a good one.**
>
> The obvious way to check for disagreement is to call the model twice and
> compare. But two identical calls at temperature 0 are *the same request*, so
> **the cache serves the second one from the first.** The answers are
> byte-identical. Disagreement is never detected. Escalation rate is 0%. Your
> cascade reports the small model's accuracy at the small model's price, and
> **nothing errors** — the only symptom is `escalated = 0.00`.
>
> The fix: draw the second sample at temperature > 0, which changes both the
> sampling *and* the cache key.
>
> **Then check whether the trigger means anything at all.** Measure how often
> the two samples agree when the answer is *right* versus when it is *wrong*.
> The reference solution measured 94% vs 83% — which caught only 2 of 12 errors.
> Disagreement detects **variance**; what the model actually has is **bias**. It
> is not unsure, it is *consistently wrong*. Reporting that, with numbers, is
> full marks.

### Part D — Is your difference real? (20 min)

**Why.** This is the intellectual core of the lab, and the skill you will use
for the rest of your career.

**What.** Two tests, on every comparison you want to claim.

**How.**

**D1 — Confidence interval.** Your measured accuracy is an *estimate*. The
interval says how much it could wobble:

```
CI ≈ p ± 1.96 × sqrt( p(1-p) / n )
```

At n = 60 and p = 0.90, that is roughly **±0.076**. So 0.88 and 0.91 have
intervals that overlap almost entirely. **You cannot conclude anything.**

Run this — it is twenty seconds and it is the most persuasive thing in the lab:
```bash
python labs/lab2/stats.py
```

**D2 — Paired test.** Do better. Both configurations saw the *same* 60 tickets,
so compare them ticket by ticket and ignore the ones where they agree:

- **b** = A right, B wrong
- **c** = B right, A wrong

If b and c are close, neither is better. `paired_test()` in `stats.py` does it.

*Why pairing wins:* the biggest source of variance is that **some tickets are
just harder than others**. Comparing overall percentages makes you fight that
noise. Comparing the same tickets cancels it out completely.

**D3.** Report b, c, the p-value, and your conclusion. **"No significant
difference" is a perfectly good answer** — it means: choose on cost.

### Part E — Error analysis and the recommendation (25 min)

**Why.** An average tells you *how much* is wrong, never *what* is wrong. Only
reading failures does that.

**What & how.**
1. Take your best configuration. **Read 20 failures.** Actually read them.
2. Group them. Name the top three groups with counts.
3. For your worst field, build the confusion matrix. There is a specific
   systematic confusion hiding in this dataset that the average conceals.
4. Write the recommendation: **a configuration, three numbers, the annual cost
   at 10,000 tickets/day, and one condition that would change your mind.**

> **Calibration.** On the test split the reference measured `SMALL` zero-shot at
> 0.930 / $0.080 / 2,276 ms, and `MAIN` zero-shot at 0.942 / $0.382 / 6,720 ms.
>
> **4.8× the cost and 3× the latency, for a difference the paired test could not
> distinguish from noise (p = 0.71).**
>
> *"The expensive configuration is not detectably better, therefore ship the
> cheap one"* is a complete and correct recommendation.

---

## How this connects to the theory

Lab 2 is the practical half of **T3**, and it settles a debt from **T1** and
**T2**.

| Theory | Where it shows up in Lab 2 |
|---|---|
| **T1 §2 — the four resources** (tokens, money, latency, attention) | The whole grid. Every row is a different trade between them. |
| **T1 §5 — the economics** | Part E's annual cost at 10k/day. The 4.8×-for-nothing result is T1's money slide, measured. |
| **T2 §2.2 — few-shot: pick edges, not averages** | Part A1. And Part A's null result *validates* T2 §3.2: descriptions already carried the rules. |
| **T2 §3.3 — field order matters** | `TicketRecordReasoned` puts `reasoning` **first** so it conditions the answer instead of rationalising it. |
| **T2 §4 — routing and cascades** | Part C, including why "ask the model for its confidence" does not work. |
| **T3 §1 — you cannot see improvement** | The reason the lab exists. |
| **T3 §2 — golden sets, dev/test discipline** | Part A4. Iterate on dev; test is not for tuning. |
| **T3 §3.1 — field vs record accuracy** | Both are in the table, and they disagree. Field accuracy is the engineering metric; record accuracy is what the business feels. |
| **T3 §4 — significance** | Part D, entire. Wilson intervals and McNemar's test. |

**The single sentence that carries both T3 and this lab:**

> ### No number, no claim.

---

## What you are graded on — and the thing that surprises people

**There is no accuracy target in this lab.** None. You are graded on the
*quality of your decision* and the *evidence behind it*.

| Criterion | Weight |
|---|---|
| Harness quality — reproducible, cached, stable | 20% |
| Experimental discipline — one variable at a time, dev/test respected, A4 handled | 25% |
| Statistical honesty — CIs, paired test, no claim beyond evidence | 20% |
| Cascade — implemented, three numbers reported *and interpreted* | 15% |
| Recommendation — specific, quantified, falsifiable, change-my-mind condition | 20% |

When the reference solution ran this grid, the honest answer was: **"none of the
clever configurations beat the cheap baseline by a detectable margin, so ship
the cheap one."**

Reaching that conclusion with the tests to back it is **full marks**. Inventing
an improvement is not. Your report must contain **at least one negative result**
— and that is not a penalty box, it is the point.

---

## Before you start

- [ ] Lab 1 is finished. Lab 2 imports your `extract.py` — a broken Lab 1 is a
      broken Lab 2.
- [ ] Read `aip/evals.py`. **All of it.** It is the instrument; you are
      responsible for knowing what it measures.
- [ ] Run `python labs/lab2/stats.py` and understand its output.
- [ ] `make check` passes.

## A note on providers

Everything in this lab is calibrated on **Gemini** — use it if you can.

`AIP_PROFILE=nvidia` works and is fully verified, with two differences you must
know about:

- It is roughly **7–10× slower**. Use `--n 20` rather than the full 60, or start
  the grid and go read `aip/evals.py` while it runs.
- NVIDIA **publishes no per-token prices**, so the harness prints `UNPRICED` and
  gives you **token counts** instead of dollars. Compare variants on tokens —
  cost is proportional to them, so the ranking is unchanged.

That second point is worth pausing on. The harness *could* have printed `$0.00`
and looked tidy. It refuses to, because a cost meter that silently reports zero
for a paid API is exactly the class of bug this module exists to teach you to
hate.
