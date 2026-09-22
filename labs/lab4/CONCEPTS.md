# Lab 4 — Concepts
### Keep this open while you work

| Concept | In the code | In the theory |
|---|---|---|
| Context assembly, numbered sources | `aip/retrieval.py::format_context` | T4 §6.1 |
| Grounding and citation validity | your `validate_answer` | T4 §6.1 |
| Refusal, both directions | `rag.py::REFUSAL` | T4 §6.2 |
| Partial answers | Q37 | T4 §6.3 |
| Precision and recall | your C3 | T3 §3.3 |
| LLM-as-judge | `aip/evals.py::llm_judge` | T3 §4 |
| Single-criterion rubrics | `JUDGE_RUBRIC_*` | T3 §4.2 |
| **Cohen's κ** | `aip/evals.py::judge_agreement` | **T3 §4.3, named only** |
| Judge biases | your D3 | T3 §4.1 |
| Stage separation | `--gold-context` | T3 §3.4 |
| Delimiting untrusted text | `aip/guards.py::delimit_untrusted` | T2 §5 |

---

## Context assembly and numbered sources

**What it is.** Retrieved chunks are formatted into a numbered block that goes
into the prompt. The numbering is the load-bearing part.

**In the code.** `aip/retrieval.py::format_context`.

**In the theory.** T4 §6.1.

**Why numbering matters.** The model can only legitimately cite a number you
supplied. So `[7]` when five sources were given is a **provable** error, found
by three lines of regex — no judge, no model, no cost.

**The general move.** Design the output so that a class of error becomes
checkable in code, then check it there — rather than asking a model whether it
lied. It is the same instinct as Lab 1's Part C.

---

## Grounding, and what citation validity does and does not buy

**What it is.** Every factual sentence carries `[n]` pointing at a supplied
source, and the indices are validated before the answer is returned.

**In the code.** Your `validate_answer()` — checks the range, checks the answer
is non-empty and untruncated, checks a non-refusal has at least one citation.

**In the theory.** T4 §6.1.

**Why the target is 1.00** where faithfulness is only ≥ 0.90: citation validity
is a **code guarantee**. You control the failure path, so anything below 1.00 is
your bug. Faithfulness is a model behaviour judged by another model, and no
amount of prompting makes it certain.

**The gap between them.** A sentence can carry a perfectly valid citation and
still not be supported by it. Validity checks that the pointer exists;
faithfulness checks that it holds up. Knowing which of your metrics is
mechanical and which is judged is most of what separates an engineered system
from a prompted one.

---

## Refusal, in both directions

**What it is.** When the sources do not contain the answer, say so — in an
**exact, machine-detectable string** given verbatim in the prompt.

**In the code.** `REFUSAL` in `rag.py`.

**In the theory.** T4 §6.2.

```
refusal recall    = correctly refused / should have refused     (of the 5)
refusal precision = correctly refused / total refused           (of your declines)
```

**Why both, always.** A system that refuses everything scores **recall 1.00** and
precision ≈ 0.11, and is useless. Reporting one number is the classic way to
make a bad system look good.

**The noise problem.** There are 5 unanswerable questions. One case moves
precision by ~0.12 and recall by 0.20. Report the **raw counts** next to the
ratios (`3/5`, not `0.60`) and do not claim a difference under about 0.15.

**Partial answers.** Q37 confirms a Platinum international benefit exists but the
addendum with the limit is missing. Refusing the whole thing throws away a
supportable fact; answering it invents a number a customer will act on. State
what is supported, refuse the rest.

**Setting the threshold is a product decision.** "Higher precision" is not a
reason. A reason is a claim about the **relative cost of the two error types**:
a wrong claim deadline can cost a customer a valid claim and cost you a
regulatory finding; an unnecessary refusal costs an agent two minutes.

---

## LLM-as-judge

**What it is.** Using a model to score outputs against a rubric, when the thing
you want to measure has no deterministic test.

**In the code.** `aip/evals.py::llm_judge`, `JUDGE_RUBRIC_FAITHFULNESS`,
`JUDGE_RUBRIC_CORRECTNESS`.

**In the theory.** T3 §4.

**Two rubrics, not one.** Faithfulness (is every claim supported by the supplied
context?) and correctness (does it match the gold answer?) measure different
things and **can disagree** — an answer can be faithful and wrong, or correct
from world knowledge and unsupported. Collapsing them into "quality" hides which
one failed, and that disagreement is diagnostic: it is what caught the
truncation bug.

**Known biases (T3 §4.1).** Position (order of presented options), verbosity
(longer looks better), and **self-preference** — models score their own output
more favourably. That last one biases **upward**, which is the direction that
gets systems shipped. If your judge is your generator, say so and say which way.

---

## Cohen's κ — the judge's licence to speak

**What it is.** Agreement between two raters, **corrected for the agreement you
would get by chance**. That correction is the whole point: if 90% of answers are
faithful, a judge that says "faithful" every time agrees with you 90% of the
time and knows nothing.

```
κ = (observed agreement − chance agreement) / (1 − chance agreement)
```

κ = 1 is perfect; κ = 0 is chance; below 0 is worse than chance.

| κ | Read as |
|---|---|
| < 0.20 | None |
| 0.21–0.40 | Fair — **not good enough to report a number** |
| 0.41–0.60 | Moderate — the module's floor |
| 0.61–0.80 | Substantial |
| > 0.80 | Near-perfect (be suspicious; usually an easy criterion) |

**In the code.** `aip/evals.py::judge_agreement`.

**In the theory.** T3 §4.3 names it and sets the ≥ 0.4 bar. The arithmetic above
is not in the lectures.

**The procedure, and the order matters.** Hand-label 20 answers **before** you
look at what the judge said. Seeing its labels first anchors yours, and κ then
measures how well you copied it rather than whether it is right.

**When κ is low, fix the rubric, not the model.** Read your disagreements. You
will almost always find your own labelling rule was implicit — the same thing
that made `urgency` unlearnable in Lab 1 until the scale was written down.

**The rule.** You may not report a judged number in this lab without its κ.

---

## The truncated judge — a worked failure

Faithfulness was first measured at **0.667**. The true value was **0.933**.

`llm_judge` capped output at 512 tokens. The judge tier is a reasoning model
that spent most of that budget on invisible thinking, so its JSON verdict was
cut off mid-object, failed to parse — **and the parse failure was scored 0**.

Nothing errored. The only symptom was a number that looked disappointingly
plausible for a first attempt.

**Three cheap signals caught it**, and all three are habits worth keeping:

1. **An internal contradiction** — 8 of the 15 "unfaithful" answers were
   simultaneously judged *fully correct*.
2. **A deterministic cross-check** — every number in 14 of the 15 was present in
   the corpus. A free check contradicting an expensive one wins your attention.
3. **Reading the raw output**, which ended mid-token.

**The rule it produced.** *A parse failure is missing data, not a failing
answer.* Scoring it 0 puts a silent, systematic, **downward** bias on your
headline metric. `llm_judge` now retries at double the budget and returns
`parse_error`; `_score()` returns `None` so the case is excluded.

**Check what your own harness does with a judge that fails to parse** before you
trust any number it has given you.

---

## Stage separation: the gold-context decomposition

**What it is.** Run the generator twice on the answerable questions — once with
your retrieved context, once with the **gold** documents — and subtract.

```
A = correctness with GOLD context        <- the generation ceiling
B = correctness with RETRIEVED context   <- your system
retrieval-attributable loss  = A − B
generation-attributable loss = 1 − A
```

**In the code.** `evaluate.py --gold-context`, `rag.py::answer_with_gold_context`.

**In the theory.** T3 §3.4, and T4 §5 calls it the single most useful experiment
in RAG debugging.

**Why it is worth the extra run.** Without it, "RAG is bad" has seven possible
causes and you guess. With it you have two numbers and a direction, for ten
minutes of setup. If A = 0.95 and B = 0.72, work on retrieval. If A = 0.78, no
retrieval improvement will save you.

**Measured here:** A = 0.893, B = 0.821 → retrieval 0.072, generation **0.107**.
Generation is the larger loss, which is not what most people predict — and it is
what points Lab 5 somewhere non-obvious.
