# Lab 2 — The Prompt Lab: Build the Harness, Then Let It Choose
**3 hours · Individual · Prepared by T3**

---

## The problem

You finished Lab 1 with a working extractor and an opinion about why it works.

Your opinion is not evidence.

There are at least twelve reasonable configurations of that extractor, and you
have tried one. Somebody is going to ask which one to deploy, and "this one
felt good" is not an answer they can act on.

**Build an experiment harness, run the grid, and produce a recommendation
defensible on quality × cost × latency.**

### The grid

| Axis | Levels |
|---|---|
| Prompt strategy | zero-shot · few-shot (6 examples) · few-shot + reasoning field |
| Model tier | `SMALL` · `MAIN` |
| Routing | single call · small→large cascade on validation failure or low agreement |

That is 3 × 2 + cascade = at least 7 runs. On 60 dev cases with caching, this
costs a few cents and about ten minutes.

### Targets

| Requirement | Target |
|---|---|
| A defensible recommendation | with the table that supports it |
| Cascade escalation rate | reported, with blended cost — and **non-zero**, see the warning in Part C |
| Statistical honesty | no claim of a difference smaller than your confidence interval |
| Every configuration in the grid | run on dev, reported on one table |
| Cost of the best configuration | reported per 1,000 tickets and per year at 10k/day |

**Note that there is no accuracy target.** This lab is graded on the quality of
the decision and the evidence behind it, not on the number. That is deliberate,
and it reflects what actually happens: when the reference solution ran this
grid, the honest answer was *"none of the clever configurations beat the cheap
baseline by a statistically detectable margin, so ship the cheap one."*
Reaching that conclusion, with the paired tests to support it, is full marks.
Inventing an improvement is not.

---

## Timetable

| Time | Part | What you do |
|---|---|---|
| 0:00–0:10 | Setup | Read `aip/evals.py`. All of it |
| 0:10–0:50 | **A** | Few-shot selection — and why choosing examples is a retrieval problem |
| 0:50–1:30 | **B** | Run the grid. Build the comparison table |
| 1:30–2:00 | **C** | The cascade |
| 2:00–2:20 | **D** | Is your difference real? Confidence intervals and paired tests |
| 2:20–2:45 | **E** | Error analysis and the recommendation |
| 2:45–3:00 | Show & tell | Your table, your recommendation, your negative result |

---

## Part A — Few-shot selection (40 min)

**A1.** Pick 6 examples from the dev set, by hand. Do not pick typical ones —
T2 §2.2. Justify each in one line: what does this example teach that prose
cannot?

**A2.** Implement `variants.py::few_shot_block()` to render them into the
prompt. Keep the format identical to the output format you are asking for; a
mismatch between example format and requested format is a common and
embarrassing source of malformed output.

**A3.** Run zero-shot and few-shot on dev and compare.

```bash
python labs/lab2/grid.py --variants zero_shot few_shot --split dev
```

**A4 — the question that matters.** Your 6 examples came out of the dev set,
and you will now measure on the dev set. Name the problem with that. Fix it,
and say in your report what you did. (There is more than one defensible fix.)

> **Checkpoint — and prepare to be annoyed.** Few-shot may buy you *nothing*.
> When the reference solution ran this comparison, few-shot moved field accuracy
> from 0.928 to 0.931 and moved record accuracy *down*, with a paired p-value of
> 1.00. The reason is instructive: the zero-shot prompt already carries the
> labelling rules in its Pydantic field `description`s, which is exactly where
> T2 §3.2 says to put them, so the examples had nothing left to teach.
>
> If few-shot buys you 20 points, that is not a win — it means your zero-shot
> prompt was under-specified, and the honest fix is to improve it rather than
> bank the inflated delta.

---

## Part B — Run the grid (40 min)

```bash
python labs/lab2/grid.py --all --split dev --save reports/lab2_grid.json
```

Produce the table. It must have one row per configuration and columns for:

```
record_accuracy | field_accuracy | schema_valid | repair_rate |
cost_usd | cost_per_1k_tickets | p50_ms | p95_ms
```

Then answer, in your report:

1. Which axis moved the numbers most — prompt, or model tier?
2. What did the reasoning field cost in output tokens, and what did it buy?
   Express it as accuracy points per rupee.
3. Is there a configuration that is worse than another on **every** axis? Say
   so explicitly — dominated configurations are a real and useful finding.

---

## Part C — The cascade (30 min)

Implement `cascade()` in `variants.py`:

```
   SMALL model
       │
       ├── validates AND evidence is non-empty ──▶ accept
       │
       └── otherwise ──▶ MAIN model ──▶ accept, or flag for review
```

Report:

- **escalation rate** — what fraction went to the large model?
- **blended cost** — and compare it to both pure configurations
- **blended accuracy** — and compare it to both pure configurations

> **The silent bug you will hit.** The obvious way to detect disagreement is to
> draw two samples with the same prompt at temperature 0. Those are the *same
> request*, so the response cache serves the second from the first, the answers
> are byte-identical, disagreement is never detected, the escalation rate is 0%,
> and your cascade reports the small model's accuracy at the small model's price
> while appearing to work. **Nothing errors.** The only symptom is
> `escalated = 0.00`. The fix: draw the second sample at temperature > 0, which
> changes both the sampling and the cache key.
>
> **Then measure whether the trigger carries any signal at all.** Compute how
> often your two samples agree when the answer is right, versus when it is
> wrong. If those rates are close, disagreement tells you nothing: the model is
> *consistently* wrong, not uncertain — self-consistency detects variance, and
> what you have is bias. The reference solution measured 94% agreement when
> correct against 83% when wrong, which caught only 2 of 12 errors and produced
> a cascade worth almost nothing. Reporting that, with the numbers, is full
> marks; a cascade you did not interrogate is not.

---

## Part D — Is your difference real? (20 min)

Configuration A scores 0.88 on 60 cases. Configuration B scores 0.91. Is B
better?

**D1.** Compute the 95% confidence interval for each, using the normal
approximation:

```
CI ≈ p ± 1.96 · sqrt( p(1-p) / n )
```

At n = 60 and p = 0.90, that half-width is about 0.076. Your two intervals
overlap heavily. **You cannot conclude B is better from these numbers.**

**D2.** Do better: run a **paired** comparison. Same 60 items, both systems.
Count only the items where they disagree:

- b = cases where A is right and B is wrong
- c = cases where B is right and A is wrong

McNemar's test on (b, c). With small counts, the exact binomial is fine:
`scipy.stats.binomtest(min(b,c), b+c, 0.5)`. `paired_test()` in
`labs/lab2/stats.py` implements it.

Pairing removes the between-item variance, which is the dominant variance
component here, and it routinely detects differences that unpaired comparison
cannot at the same n.

**D3.** State, for your chosen comparison: b, c, the p-value, and your
conclusion. **"No significant difference" is a perfectly good result**, and it
tells you to choose on cost instead.

---

## Part E — Error analysis and recommendation (25 min)

**E1.** Take your best configuration. Read 20 failures. Cluster them. Name the
top three clusters with counts.

**E2.** For your worst-performing field, produce the confusion matrix and say
what it reveals. There is a specific systematic confusion in this dataset that
the aggregate accuracy hides. Find it.

**E3.** Write the recommendation. One paragraph. It must name a configuration,
give the three numbers, state the annual cost at 10k tickets/day, and state
one condition under which you would change your mind.

For calibration: on the test split the reference solution measured `SMALL`
zero-shot at 0.930 field / $0.080 / 2,276 ms p95, and `MAIN` zero-shot at
0.942 / $0.382 / 6,720 ms — **4.8× the cost and 3× the latency for a difference
the paired test could not distinguish from noise (p = 0.71)**. Your grid may
land differently. If it lands the same way, say so plainly: "the expensive
configuration is not detectably better, therefore ship the cheap one" is a
complete and correct recommendation.

---

## Deliverables

1. `labs/lab2/variants.py` — your configurations, including the cascade
2. `report.md` — at most three pages:
   - the grid table
   - the few-shot selection justification, and your answer to A4
   - the cascade numbers (escalation rate, blended cost, blended accuracy)
   - the paired-test result with b, c, and p
   - three error clusters, and the confusion matrix from E2
   - the recommendation paragraph
   - **at least one negative result**
3. `reports/lab2_grid.json`

---

## Rubric (9% of Module 1)

| Criterion | Weight | Full marks means |
|---|---|---|
| Harness quality | 20% | Runs the grid reproducibly; caching works; results are stable across re-runs |
| Experimental discipline | 25% | One variable at a time; dev/test respected; A4 handled honestly |
| Statistical honesty | 20% | CIs computed; paired test run; no claim beyond the evidence |
| Cascade | 15% | Implemented, and the three numbers reported and interpreted |
| Recommendation | 20% | Specific, quantified, falsifiable, and includes a change-my-mind condition |

---

## Stretch

1. **Self-consistency.** Sample n=5 at T=0.7, majority vote. Plot accuracy
   against disagreement rate. Does disagreement predict error better than the
   model's own stated confidence? (It does. Show by how much.)
2. **Dynamic few-shot.** Retrieve the 6 most similar labelled examples per
   ticket instead of using a fixed 6. You need `aip.embed`. Compare against
   fixed few-shot — this is a preview of Lab 3.
3. **Prompt-length ablation.** Delete one instruction at a time from your
   system prompt and re-run. Which instructions are load-bearing? Most are not.
4. **Cross-provider.** Run your best configuration on a second provider profile
   (`AIP_PROFILE=nvidia`, which is verified, or `ollama` for fully local).
   Report the portability gap. Two things you will hit, both instructive:
   NVIDIA is roughly **7-10x slower** on this task, so use `--n 20`; and it
   publishes **no per-token prices**, so the harness reports `UNPRICED` and
   gives you tokens instead of dollars. Compare on tokens — cost is
   proportional to them — and say in your report why a cost meter that printed
   `$0.00` there would have been worse than one that refuses to guess.
