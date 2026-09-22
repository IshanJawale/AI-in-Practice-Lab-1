# Lab 4 — RAG v1: Grounded Answers with Citations
### Note for students · read before the lab

> **In one line.** An answer without a source is a liability in a regulated
> business — and before you may report a number produced by an LLM judge, you
> have to earn the right to use it.

> **Working through the lab?** [`CONCEPTS.md`](CONCEPTS.md) is the reference to
> keep open beside your editor — every concept the lab uses, what it is, where
> it sits in the code, and where it came from in the theory.
---

## Why this lab exists

Lab 3 gave you a retriever that puts the right document in the top five about
85% of the time. Agents still have to read the passages themselves. Today you
generate the answer — and the moment you do, an insurance helpdesk acquires two
hard constraints that a chatbot demo does not have.

**Every factual sentence carries a citation**, validated in code. And **when the
sources do not contain the answer, the system says so** rather than guessing.
The second is where systems like this usually fail, which is why 5 of the 45
golden questions are unanswerable and why you measure refusal in *both*
directions.

There is a second thread running through the lab, and it is the more important
one. You are about to start measuring things with a model. That instrument needs
calibrating like any other, and this module's own materials contain the cautionary
tale: faithfulness was first measured at **0.667** when the true value was
**0.933**, because the judge's output was silently truncated and a parse failure
was scored as zero. Nothing errored. The number just looked plausibly
disappointing.

**Where it sits.** The failures you produce today are Lab 5's backlog — bring
them. The pipeline you build here is what Lab 6 adds tools to and Lab 7 ships.

---

## What you will build

- An **answer prompt** with a source-only rule, an exact refusal string, and a
  policy for contradictory sources
- **Citation validation in code** — target 1.00, because it is a code guarantee
  and not a model behaviour
- **Refusal**, measured in both directions, including one question that needs a
  *partial* answer
- **Two single-criterion judges** — faithfulness and correctness — each with a
  **Cohen's κ against your own hand labels**
- The **gold-context decomposition**: the single most useful experiment in RAG
  debugging, and the one that tells you how to spend Lab 5

---

## How to approach it

**The step people underestimate is judge calibration (D2), and it is required.**
Twenty hand labels against each rubric, done *before* you look at what the judge
said. Budget the full 45 minutes for Part D. You may not report a judge number
in this lab without its κ, and κ is 25% of the rubric.

Do the hand labelling as a pair, independently, then compare. Where the two of
you disagree is almost always where your rubric is implicit — and that is the
same thing the judge is struggling with.

**Run E2 even if you are short of time.** It is one extra evaluation run and it
decides what you do for the whole of next week.

---

## Where this comes from in the theory

| Theory | What it claimed | Where you meet it today |
|---|---|---|
| **T4 §6.1** — three non-negotiable rules | Source-only, cite by index, exact refusal string | Part A. Write `ANSWER_SYSTEM` before reading the reference |
| **T4 §6.2** — the refusal trade-off | Refusing more is not strictly better | Part C. Both directions, at two strictness settings |
| **T4 §6.3** — contradictions | Surface the conflict, do not pick silently | Part A rule 5, and the archived-document questions |
| **T4 §5** — the seven failure modes | Exactly one stage usually failed | E3. Tag ten wrong answers; this is your Lab 5 backlog |
| **T3 §3.1** — deterministic metrics | Free and unarguable; prefer them | Citation validity. Three lines of regex, target 1.00 |
| **T3 §3.4** — separate the stages | Measure retrieval and generation apart | E2, the gold-context decomposition |
| **T3 §4.1** — judge biases | Self-preference, position, verbosity | D3. If your judge is your generator, say so and say which way it biases |
| **T3 §4.2–4.3** — earning the judge | Single criterion, κ ≥ 0.4, fix the rubric not the model | D1 and D2. The gate on reporting any judged number |
| **T1 §3 #4** — truncation | Check `finish_reason` | The war story in the handout. It happened to this course's own harness |

---

## Hints

- **Numbering the sources is what makes one class of hallucination provable.**
  `[7]` with five sources is a mechanical error — no judge, no cost. Design so
  that errors become checkable in code, then check them there.
- **Citation validity below 1.00 is a code bug, not a prompt problem.** You
  control the failure path; decide what it does and defend the choice.
- **Q37 needs a partial answer**, not a refusal and not an invention. Most
  systems do one of the other two on the first attempt.
- **Report refusal counts alongside refusal ratios.** With 5 unanswerable
  questions, one case moves precision by 0.12. `3/5` makes that visible;
  `0.60` hides it.
- **If κ comes out low, read your disagreements before you touch the model.**
  You will usually find your own labelling rule was never written down — the
  same thing that made `urgency` unlearnable in Lab 1.
- **Check what your harness does with a judge that fails to parse.** If it
  scores it zero, every number it has ever given you is biased downward.

---

## What separates a good report from an adequate one

- An adequate report gives faithfulness and correctness. A good one gives them
  **with κ**, and says what it changed when κ was too low.
- An adequate refusal section gives precision. A good one gives **both rates at
  two settings**, and a product recommendation grounded in the relative cost of
  the two error types — not in "precision matters more".
- The **decomposition** is the highest-value table in the report. A and B, the
  two attributed losses, and one sentence saying where Lab 5 will go.

---

## Questions we will discuss

1. Your decomposition probably says generation is the larger loss. Did you
   expect that? What would you have worked on if you had not measured it?
2. Refusal precision and recall trade against each other. For an insurance
   helpdesk, what is the exchange rate — how many unnecessary refusals is one
   invented claim deadline worth?
3. Your judge and your generator may be the same model family. Which direction
   does that bias your numbers, and by roughly how much would you guess?
4. Citation validity is 1.00 and faithfulness is 0.93. A sentence can carry a
   valid citation and still not be supported by it. What would it take to close
   that gap mechanically?
