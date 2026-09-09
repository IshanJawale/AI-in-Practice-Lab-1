# T3 — Evaluation-Driven Development for Non-Deterministic Systems
**AI in Practice I · Module 1 · Theory 3 of 4 · 90 minutes**

> **Prepares you for:** Lab 2 (The Prompt Lab) and every lab after it
> **Assumes:** precision / recall / F1 from the ML course. We will use them, not derive them.

---

## Running order

| Min | Segment |
|---|---|
| 0–10 | §1 The problem: you cannot see whether it got better |
| 10–30 | §2 Building a golden set that is worth having |
| 30–50 | §3 Choosing metrics that mean something |
| 50–70 | §4 LLM-as-judge, and how to earn the right to use it |
| 70–85 | §5 The experiment loop, regression gates, and error analysis |
| 85–90 | Lab 2 briefing |

---

## 1. You cannot see whether it got better

Ordinary software has a property you have never had to think about: it is
deterministic. Run the test, get the answer. A GenAI system has none of that.

- The same input can give different outputs.
- A change that fixes case A can break case B, invisibly.
- The model behind your API can change under you, without notice.
- "Better" is often a judgement call, not a comparison.
- Your intuition about quality is formed by whichever ten examples you happened
  to look at, and those are not a sample.

Consequence:

> **In applied GenAI, the evaluation harness is not a testing activity that
> follows development. It is the instrument that makes development possible.
> Build it first.**

This is not a moral position, it is an economic one. Without a harness, every
prompt change is a coin flip you cannot observe. Teams without harnesses do not
iterate slowly — they iterate *randomly*, and plateau at whatever their first
guess achieved. Teams with harnesses compound.

### 1.1 The rule for this module

You will hear this in every lab, because it is the single habit worth taking
away:

> **No number, no claim.**
> "It's better now" is not a result. "Record accuracy 0.71 → 0.94 on the
> 120-item test split, cost 1.8×, p95 +340 ms" is a result.

---

## 2. The golden set

A golden set is a collection of inputs with known-good outputs. Everything else
in evaluation depends on it, and almost every failed eval effort failed here.

### 2.1 How big?

Smaller than you think, and it is far more important that it is *representative*
than that it is large.

| Size | What it buys |
|---|---|
| 10–20 | Smoke test. Catches gross breakage. Not a measurement. |
| **50–100** | **The practical minimum for comparing two variants.** |
| 200–500 | Reliable enough to detect a few points of difference. |
| 1,000+ | Rarely worth it before you have a real user population to sample from. |

The statistics: at n = 100, a measured accuracy of 0.90 has a 95% confidence
interval of roughly ±0.06. So **a 3-point difference on a 100-item set is not a
result** — it is inside the noise. Either grow the set or run paired
comparisons (same items, both systems, count the items where they differ).
Lab 2 will make you feel this.

### 2.2 What goes in it

Not a random sample. A random sample of a support queue is 80% easy tickets,
and you will spend your evaluation budget re-confirming that easy things are
easy. Stratify deliberately:

| Stratum | Share | Why |
|---|---|---|
| Typical cases | ~40% | The baseline you must not regress |
| Hard but valid | ~25% | Where the differences between variants show up |
| Edge cases | ~15% | Empty input, one word, 10,000 words, wrong language, mixed script |
| Adversarial | ~10% | Injection attempts, contradictory content |
| **Should-fail** | ~10% | Questions with no answer. **The most-skipped and most-informative stratum.** |

That last row deserves a note. A system that answers everything scores well on
a golden set that only contains answerable questions, and it is dangerous in
production, because it also confidently answers the questions it should have
refused. Our RAG golden set (`data/eval/rag_golden.jsonl`) is 11% unanswerable
for exactly this reason.

### 2.3 Where to get labels

In descending order of quality:

1. **Production outcomes.** Did the user accept the suggestion? Did the ticket
   get re-routed? Free, real, and unavailable at the start.
2. **Human labels from a domain expert.** Expensive and correct.
3. **Human labels from you.** Fine, if you write the labelling rules down
   first. Two hours of labelling 100 items is the best-spent two hours in the
   project.
4. **Synthetic, generated from a source of truth.** Our ticket set does this:
   the text is generated *from* the label, so labels are exact.
5. **Labels from a stronger model.** Acceptable as a bootstrap, only if you
   hand-verify a sample and report the agreement.

### 2.4 The splits, and the discipline

```
dev  (60)  ── you look at these, iterate on these, debug on these
test (120) ── you run these rarely, and you never read the failures in detail
blind (60) ── the instructor holds the labels
```

The discipline is the point. Iterating against the test set means you are
fitting your prompt to it — the same overfitting as in classical ML, with the
same consequence: your reported number is optimistic and your system does not
transfer. **You may look at dev failures freely. Run the test set when you have
a candidate, and report what it says.**

If your dev score is 0.94 and your test score is 0.81, that gap *is* a result.
Report it. It tells you and everyone else something true about your process.

---

## 3. Metrics that mean something

### 3.1 Prefer deterministic metrics; they are free and unarguable

| Task | Metric | Note |
|---|---|---|
| Classification | accuracy, per-class F1, confusion matrix | **Always look at the confusion matrix.** Aggregate accuracy hides that you are systematically confusing exactly two classes, which is a fixable, specific problem |
| Extraction | field accuracy **and** record accuracy | See below |
| Retrieval | hit_rate@k, recall@k, MRR, nDCG@k | §3.3 |
| Format | validity rate, repair rate | Free, and it is the reliability number |
| Refusal | refusal precision / recall on the unanswerable stratum | Did it refuse when it should, and only then? |

**Field accuracy vs record accuracy.** Six fields per record, 95% accurate
each, independent errors: field accuracy 0.95, but record accuracy is
0.95⁶ = **0.74**. A quarter of your records have at least one error and need a
human. Field accuracy is the engineering metric; record accuracy is the
business metric. Report both, and know which one your stakeholder is asking
about.

### 3.2 Always report the triple

Quality alone is not a result. Every evaluation in this module reports:

```
        quality  ×  cost  ×  latency
```

A configuration that is 2 points better for 30× the money is usually worse.
A configuration that is 1 point worse and 5× faster may be the right answer for
an interactive product and the wrong answer for a batch job. **You cannot make
the trade-off if you only measured one axis**, and the person who only measured
quality has not finished the work.

### 3.3 Retrieval metrics, and which one to care about

For a query with a set of relevant documents and a ranked list of retrieved ones:

- **hit_rate@k** — did *at least one* relevant document make the top *k*?
- **recall@k** — what fraction of all relevant documents made the top *k*?
- **precision@k** — what fraction of the top *k* are relevant?
- **MRR** — 1/rank of the first relevant document, averaged over queries.
- **nDCG@k** — rank-discounted gain; the general-purpose comparison metric.

**For RAG specifically, hit_rate@k is usually the metric that matters**, because
the generator only needs one good passage to produce a correct answer. Optimising
nDCG when hit_rate is already 0.98 is optimising the wrong thing.

But precision@k matters too, for a reason that is not about ranking: every
irrelevant chunk in the context costs input tokens, adds distractors that
measurably degrade generation, and pushes the good chunk toward the middle of
the window where it is attended to less. **Retrieval quality and generation
quality are not independent.** This is the argument for retrieve-wide-then-rerank.

### 3.4 Separate the stages, always

The single most useful structural decision in evaluating a RAG system:

```
retrieval eval          generation eval
(needs: labelled        (needs: gold answers,
 relevant docs)          given GOLD context)
        │                        │
        └──────────┬─────────────┘
                   ▼
            end-to-end eval
```

Evaluate generation **with gold context** as well as with retrieved context.
The difference between those two numbers is precisely the damage your retriever
is doing, and it converts "the answer was wrong" into either "retrieval failed"
or "generation failed" — two completely different repair jobs. Lab 5 is built
on this decomposition.

---

## 4. LLM-as-judge

For open-ended text, deterministic metrics run out. BLEU and ROUGE measure
n-gram overlap with a reference and correlate poorly with whether an answer is
actually good. So we use a model to grade.

This works. It also fails in specific, documented, avoidable ways.

### 4.1 The known biases

| Bias | What happens | Mitigation |
|---|---|---|
| **Position** | In A/B comparison, the first-presented answer wins more often | Run both orders, average. If the verdict flips, record a tie |
| **Verbosity** | Longer answers score higher, independent of content | Control for length; state it in the rubric |
| **Self-preference** | A model rates its own output above a neutral judge's rating | Judge with a different model family where you can |
| **Style over substance** | Confident, well-formatted, wrong beats hesitant and right | Rubric must name the substance criterion explicitly |
| **Scale compression** | On a 1–10 scale, everything lands 7–9 | Use 2–3 points, or a binary criterion |
| **Leniency** | Judges default to "acceptable" | Force a specific failure mode to be named |

### 4.2 Writing a rubric that works

Bad: *"Rate the answer's quality from 1 to 10."*

Good — binary, single-criterion, with the failure mode named:

```
Judge ONLY whether every claim in the ANSWER is supported by the CONTEXT.
Do not judge helpfulness, style, or whether the answer is true in the real world.
An answer stating anything not in the context is unsupported, even if correct.
Refusing when the context is genuinely insufficient counts as SUPPORTED.

Reply as JSON: {"score": 0 or 1, "unsupported_claims": [...], "reason": "one sentence"}
```

Four things that rubric does: it **isolates one dimension**, it **rules out the
confounders explicitly**, it **handles the refusal case** (otherwise refusals
score 0 and your system learns never to refuse), and it **forces the judge to
name the specific offending claims**, which both improves the judgement and
gives you something to read during error analysis.

Where one dimension is not enough, run several *separate* single-criterion
judges rather than one multi-criterion judge. Aggregating is your job, not the
judge's.

### 4.3 Earning the right to use a judge

> **Module rule: you may not report an LLM-judge number in a lab unless you
> have hand-labelled at least 20 cases and reported the judge's agreement with
> your labels.**

Use Cohen's kappa (`aip.evals.judge_agreement`), which corrects for agreement
by chance:

| κ | Reading |
|---|---|
| < 0.20 | The judge is measuring something else. Do not use it |
| 0.20–0.40 | Weak. Fix the rubric |
| 0.40–0.60 | Moderate. Usable for tracking a trend, not for a headline claim |
| 0.60–0.80 | Good. This is what a well-specified rubric achieves |
| > 0.80 | Excellent — and worth checking that your task was not trivially easy |

When κ is low, the fix is almost always the **rubric**, not the model. Read the
cases where you and the judge disagreed; usually you will find that your own
labelling rule was implicit and you never wrote it down.

### 4.4 Cost

A judge call per case is as expensive as the system call. A 120-case eval run
20 times during development is 2,400 judge calls. Manage it:

- **Cache aggressively.** `aip` does this by default: an unchanged
  (case, output) pair is judged once, ever.
- **Deterministic metrics first.** Only judge what they cannot reach.
- **Judge a stratified subsample** during iteration; judge the full set for the
  final report, and say which you did.

---

## 5. The loop

```
      ┌──────────────────────────────────────────────────┐
      │                                                  │
      ▼                                                  │
  1 BASELINE ──▶ 2 ERROR ANALYSIS ──▶ 3 HYPOTHESIS ──▶ 4 CHANGE ──▶ 5 MEASURE
  run it,        read 20 failures,    "if I do X,       ONE thing    dev set
  record it      cluster them         Y improves"                       │
                                                                        │
                        6 ACCEPT or REVERT ◀────────────────────────────┘
                        log the number either way
```

### 5.1 Error analysis is the step that is actually worth your time

Not a metaphor: **open twenty failing cases and read them.** Put them in a
spreadsheet, one row each, with a free-text "what went wrong" column. Then
cluster.

You will nearly always find that 60–80% of failures fall into two or three
clusters, and that each cluster has a specific, cheap fix — usually a field
description, one few-shot example, or a chunking change. Nobody finds those by
staring at an aggregate accuracy number, and nobody finds them by asking a
model to summarise the failures for them.

### 5.2 Change one thing

If you change the model, the prompt, and *k* at once and the score moves, you
have learned nothing transferable. One variable per run. Keep an experiment
log — `aip.evals.compare()` prints the table; paste it into your lab report.

### 5.3 Regression gates

Once you have a number you are happy with, defend it. In Lab 7 your CI runs the
harness and fails the build if a key metric drops by more than a stated
tolerance:

```yaml
- record_accuracy:  min 0.90
- citation_validity: min 0.98
- cost_per_query:   max 0.004      # USD
- p95_latency_ms:   max 3500
```

Note that the gate covers cost and latency, not only quality. In a real system
those regress too, and they regress silently.

---

## 6. Lab 2 briefing

**Problem.** You have Lab 1's extractor. You now have to decide, with evidence,
between roughly a dozen configurations: two or three prompt strategies, two or
three model tiers, with and without few-shot, with and without a reasoning
field, single-call versus a small→large cascade.

You cannot decide by looking. Build the harness, run the grid, produce a table,
and defend a recommendation on quality × cost × latency.

**Deliverable.** A one-page recommendation with the comparison table, the
confusion matrix for your chosen configuration, an error-analysis section
naming your top three failure clusters, and an explicit statement of what you
tried that did *not* work.

---

## Reading

- Zheng et al. (2023), *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* —
  arxiv.org/abs/2306.05685. §4 is the bias catalogue.
- Es et al. (2023), *RAGAS: Automated Evaluation of Retrieval Augmented
  Generation* — arxiv.org/abs/2309.15217
- Husain, *Your AI product needs evals* — hamel.dev/blog/posts/evals/
- `aip/evals.py` — read it before the lab, all of it.

## Check yourself

1. Your golden set has 100 items. Variant A scores 0.88, variant B scores 0.91.
   What do you conclude, and what would you do next?
2. Six fields, 97% accurate each. What is record accuracy? What if the errors
   are correlated rather than independent — higher or lower, and why?
3. Why must a golden set contain unanswerable questions? What specifically
   goes undetected without them?
4. Your judge has κ = 0.35. Give three concrete rubric changes to try, in the
   order you would try them.
5. A RAG system answers a question wrongly. Describe an experiment, using only
   your golden set, that decides whether retrieval or generation is at fault.
6. Why do the regression gates in §5.3 include a maximum cost?
