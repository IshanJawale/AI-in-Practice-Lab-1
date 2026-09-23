# Lab 5 — RAG v2: Diagnose, Fix, Prove
### Note for students · read before the lab

> **In one line.** The difference between engineers who improve systems and
> engineers who thrash is diagnosis before treatment — and this is the only lab
> in the module where the reference solution's fix made things *worse* and
> still scores full marks.

> **Working through the lab?** [`CONCEPTS.md`](CONCEPTS.md) is the reference to
> keep open beside your editor — every concept the lab uses, what it is, where
> it sits in the code, and where it came from in the theory.
---

## Why this lab exists

Your Lab 4 system gets roughly a quarter of the questions wrong. The instinct at
this point is to try things: a bigger model, more chunks, a different embedding.
That is how teams spend six weeks and gain two points.

The alternative is the whole lab. **Every wrong answer has exactly one stage
that failed.** Find it. Count how often each stage is at fault. Fix the biggest
cluster. Prove the fix with a before-and-after table that includes the things
that got worse.

You should know before you start what happened when the reference solution did
this. It classified correctly (13 of 14 failures were generation), chose a
well-motivated fix, predicted it would recover 4 to 6 of them — and measured
**−0.050 correctness**. The prediction was wrong in *direction*, not just
magnitude.

That is a complete Lab 5. **There is no improvement target.** What is graded is
whether you diagnosed before you fixed, predicted before you measured, and
reported what happened rather than what you hoped. A pair reporting −0.05 with a
clear account of why scores above a pair reporting +0.12 they cannot explain.

**Where it sits.** It reads `reports/lab4.json` and cannot start without it. The
pipeline you leave here is what Lab 7 ships.

---

## What you will build

- A **classification of every Lab 4 failure** into the seven modes, with
  evidence for each
- A **Pareto chart** showing that two modes account for most of them
- A **ranking by expected value** — recovery weighed against cost, latency and
  effort — and a one-sentence justification for your pick
- A **prediction**, written down before you implement
- One **fix**, measured, with a full before-and-after table and a genuine
  regression check

---

## How to approach it

**Part A is most of the lab — fifty minutes, and it is not optional.**
`diagnose.py` automates six of the seven checks; the one it cannot decide is
mode 2, chunk boundaries, because that needs someone to look at where the cut
fell and judge whether the two halves are separately retrievable.

**Write the prediction down before you touch any code.** Not in your head, in
the report. It is the difference between an experiment and a story told
afterwards.

**One fix at a time, measured each time.** If you apply three and the number
moves, you have learned nothing you can carry to the next system — and a fix
that helped may be hiding one that hurt.

---

## Where this comes from in the theory

| Theory | What it claimed | Where you meet it today |
|---|---|---|
| **T4 §5** — the seven failure modes | Exactly one stage usually failed; here is the tree | Part A. The whole lab is built on this table |
| **T4 §5 #6** — the gold-context test | The single most useful experiment in RAG debugging | The mode-6 branch. Note which way round it reads |
| **T4 §2.2–2.3** — chunking | Boundaries, overlap, small-to-big | The mode 2 fix menu |
| **T4 §4.3, §4.5** — hybrid, HyDE, multi-query | Query-side transforms for lexical mismatch | The mode 3 fix menu — and each adds a call per query |
| **T4 §4.4** — rerank narrow | Two-stage retrieval | The mode 4 and 5 fix menus |
| **T3 §5.1** — error analysis | The step actually worth your time | Part A. Fifty minutes of reading failures, deliberately |
| **T3 §5.2** — change one thing | One variable or nothing transferable | Part C rule 1 |
| **T3 §1.1** — no number, no claim | | Part D. Including the numbers that went the wrong way |

---

## Hints

- **The mode-6 test is the one people invert.** Gold context *fixing* the answer
  means **retrieval** was at fault. Still wrong with gold context means
  generation.
- **A tally spread evenly across all seven modes means you mis-classified.** A
  heavily concentrated tally is normal and is not a mistake.
- **Your distribution will not match the reference's, and should not.** Its 93%
  mode-6 concentration is a consequence of starting from Lab 3's *winning*
  retriever. If you ended Lab 3 somewhere else, your backlog is different — and
  that is exactly why you classify rather than copy.
- **When your fix and your tally disagree, stop.** Either the tally wins or the
  tally was wrong; resolving that is the work. Fixing retrieval after a tally
  that says generation measures a change against a problem that is not there.
- **If Q29–Q31 are still failing, the fix is metadata filtering and it is free.**
  If you already did it in Lab 3, say so.
- **Check refusal precision in your regression check.** Better retrieval often
  makes a system refuse *less*, which means it starts answering questions it
  should decline. That is the improvement quietly buying itself a new problem.

---

## What separates a good report from an adequate one

- An adequate report has a tally. A good one has a tally **with evidence per
  case** and a named judgement on every `needs_human_check`.
- An adequate report shows the metric it targeted. A good one shows **every Lab 4
  metric**, with whatever got worse reported prominently rather than in a
  footnote.
- A good report **re-classifies the remaining failures** and notices when
  failures have moved downstream — that is not a new problem, it is a previously
  masked one becoming visible, and saying so is the mark of someone who
  understands their own pipeline.

---

## Questions we will discuss

1. Your prediction versus what happened. If you were wrong, was your model of
   the system wrong, or was the fix a bad implementation of a good idea?
2. The reference relaxed the answer-length rule and correctness *and* refusal
   precision both fell. What is the mechanism connecting those two?
3. You ranked clusters by expected value. Did the largest cluster win? If it did
   not, what beat it?
4. Which of the seven modes is the only one with no retrieval or generation fix
   at all — and what would you actually do about a system whose failures were
   mostly that?
