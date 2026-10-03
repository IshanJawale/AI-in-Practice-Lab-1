# Lab 2 — Concepts
### Keep this open while you work

| Concept | In the code | In the theory |
|---|---|---|
| One variable at a time | `grid.py` | T3 §5.2 |
| Few-shot selection | `variants.py::FEW_SHOT_IDS` | T2 §2.2 |
| Reasoning-field placement | `TicketRecordReasoned` | T2 §3.3 |
| Model tiers | `aip/config.py::PROFILES` | T1 §2.3 |
| Cascade / routing | `variants.py::cascade` | T2 §4.2 |
| Self-consistency | your cascade trigger | T2 §4.3 |
| Cache keys and temperature | `aip/cache.py::make_key` | T1 §2.3 |
| Confidence intervals | `stats.py::wilson_interval` | T3 §2.1, §2.5 |
| The Wilson interval | `stats.py::wilson_interval` | T3 §2.5 |
| p-values | `stats.py::paired_test` | T3 §2.5 |
| McNemar's test | `stats.py::paired_test` | T3 §2.5 |
| Dominated configurations | `grid.py` | T3 §2.5 |

> **All of this is in T3 §2.5 and on the slide with the sliders.** If you were
> at that session you have seen the intervals fail to separate 0.88 from 0.91 at
> n = 60, and then seen the paired test do it. This page is the same material in
> a form you can consult mid-lab. Read it before Part D.

---

## One variable at a time

**What it is.** Every configuration in the grid runs through the same harness,
the same cases and the same metric, so the only thing differing between two rows
is the thing you intended to differ.

**In the code.** `grid.py` takes variant *names* and runs them all through one
`run_eval` with one `metric`. That is not tidiness — it is what makes the rows
comparable.

**In the theory.** T3 §5.2.

**The trap.** If you change the prompt *and* the tier between two runs, the
delta is uninterpretable and you have spent the money for nothing.

---

## Few-shot: choose the edges

**What it is.** Examples in the prompt, teaching by demonstration. They cost
input tokens on **every call, forever**, so each one has to earn its place.

**In the code.** `FEW_SHOT_IDS` and `few_shot_block()`.

**In the theory.** T2 §2.2.

**The test for including an example.** *What does this teach that a
`Field(description=…)` could not?* A boundary case, an exception, a format prose
struggles to express. A representative ticket teaches nothing the schema has not
already said — which is exactly why the reference measured few-shot at p = 1.00.

**The trap.** The example output format must be **byte-identical** to the format
you are asking for. A mismatch spends tokens teaching the model to do the thing
you are also forbidding.

---

## Reasoning-field placement

**What it is.** Two different idioms that look the same:

```python
class WithReasoning(BaseModel):
    reasoning: str      # FIRST — the model thinks here, and it conditions
    answer: Label       #         the answer. Chain-of-thought in a schema.

class WithCitation(BaseModel):
    answer: Label       # FIRST — the answer is committed, then justified.
    evidence: str       #         Cheaper. The justification is post-hoc and
                        #         can rationalise a wrong answer.
```

**In the code.** `TicketRecordReasoned`.

**In the theory.** T2 §3.3.

**The trap.** Models generate left to right, and Pydantic preserves declaration
order into the JSON Schema. Position is not cosmetic.

---

## Cascade, routing, and self-consistency

**What it is.** Run the cheap model; escalate to the expensive one only when a
trigger fires. The claim is *most of the big model's quality at most of the
small model's price*, and it needs three numbers to support it: escalation rate,
blended cost, blended accuracy.

**In the code.** `variants.py::cascade`, and `metric()` in `grid.py` reads
`_path` to compute the escalation rate.

**In the theory.** T2 §4.2 for routing, T2 §4.3 for why "ask the model how
confident it is" is *not* on the trigger list.

**Self-consistency** means: sample the same prompt twice, and treat disagreement
as a proxy for uncertainty. It detects **variance**. It does not detect **bias**
— a model that reads the urgency 1/2 boundary the same wrong way every time will
agree with itself confidently and wrongly.

**Measure whether your trigger carries signal.** Compute agreement when the
answer is right, and agreement when it is wrong. The reference got 94% and 83% —
only ~3× enriched for errors, catching 2 of 12.

**The trap.** Two samples at temperature 0 are the *same request*. The response
cache serves the second from the first, the answers are byte-identical,
disagreement is never detected, escalation is 0.00, and **nothing errors**.

---

# The statistics

## Why any of this is needed

Your dev set has 60 items. Configuration A gets 53 right, B gets 55. B looks
better by 0.033. Run the same two configurations on a *different* 60 tickets
and the ordering may reverse — not because anything changed, but because 60 is a
small sample and both numbers carry uncertainty.

Everything below exists to answer one question: **is this difference bigger than
the noise?**

---

## Confidence intervals

**What it is.** A range that would contain the true accuracy 95% of the time if
you repeated the whole experiment. Wide interval = you measured little.

The textbook formula is the **normal approximation**:

```
CI ≈ p ± 1.96 · sqrt( p(1-p) / n )
```

At n = 60 and p = 0.90 the half-width is about **0.076**. So a measured 0.90 is
consistent with anything from 0.82 to 0.98, and two configurations 3 points
apart have intervals that overlap almost entirely.

**In the theory.** T3 §2.1 and §2.5. Your dev set is smaller than the n = 100
worked there, so your intervals are wider still.

> **The half-width you actually need is not the one on either number.** ±0.076
> is how well you know *one* accuracy at n = 60. The claim you want to make is
> about the *difference*, whose interval is √2 wider — **±0.107** — so two
> unpaired measurements on 60 items have to differ by about **11 points** before
> you may say anything. That is why Part D pairs.

---

## The Wilson interval

**What it is.** A better interval for a proportion. Same purpose, different
arithmetic.

**In the code.** `stats.py::wilson_interval` — and it is what `grid.py` prints.

**Why not the normal approximation.** It breaks exactly where this lab lives —
small n, p near 1. At n = 60, p = 0.95 it gives an upper bound **above 1.0**,
which is not a probability. Wilson stays inside [0, 1] and stays honest at the
extremes by pulling the centre slightly toward 0.5.

**In the theory.** T3 §2.5. The handout gives you the normal approximation in
D1 because it is the one you can do in your head; the code uses Wilson because
it is the one you should report.

**The trap.** Wilson is often *wider* than the normal approximation where it
matters. That is the point — it is not a way to make things look significant.

---

## p-values

**What it is.** Assume there is genuinely no difference between the two systems.
The p-value is the probability of seeing a difference **at least as large as the
one you saw**, purely by chance, under that assumption.

- **Small p** (< 0.05 by convention) — what you saw would be unlikely if nothing
  were going on, so it is reasonable to believe something is.
- **Large p** — what you saw is unremarkable under "no difference". You have not
  shown there is no difference; you have failed to show there is one.

**In the theory.** T3 §2.5.

**Three things it is not:**

1. Not the probability that the systems are the same.
2. Not a measure of how *big* the difference is. A large sample can produce
   p = 0.001 on a difference too small to matter.
3. Not a licence to keep testing until one comes up small. Run seven comparisons
   at the 0.05 level against one baseline and you should expect roughly one to
   look significant by chance alone — which is worth remembering when you read
   your own grid.

---

## McNemar's test — and why pairing wins

**What it is.** The right test when two systems were run over the **same items**.

**In the code.** `stats.py::paired_test`.

```
b = A right, B wrong
c = B right, A wrong
```

Items where the two **agree** — both right or both wrong — are **discarded**.
They carry no information about which system is better. Under the null
hypothesis each discordant pair is a fair coin, so the test is: out of `b + c`
coin flips, is `min(b, c)` surprisingly small? At these counts the exact
two-sided binomial is the right answer, and it is four lines of `math.comb`.

**In the theory.** T3 §2.5, and the slider slide — where you can watch b = 4,
c = 10 give p = 0.18 and b = 2, c = 14 give p = 0.004 on the same sixty items.

**Why pairing is stronger.** Some tickets are hard for everything and some are
easy for everything. That spread — **item difficulty** — is the dominant source
of variance, and comparing two independent proportions makes you fight it.
Comparing the *same* items cancels it, because the hard items are hard for both.
Nothing about your data changed; you stopped throwing away the fact that it was
the same sixty tickets.

**Reading the output.** `b=4 c=5 p=1.00` means: nine items disagreed, and they
split as evenly as nine things can. There is no detectable difference, so decide
on cost. That is a **result**, not a failed experiment.

---

## Dominated configurations

**What it is.** Configuration X is *dominated* if some other configuration is at
least as good on **every** axis you care about — quality **and** cost **and**
latency — with at least one strictly better.

**In the code.** `grid.py` computes and prints this for you. Read the line.

**In the theory.** T3 §2.5.

**Why it is useful.** Most configuration choices are trade-offs and need a
judgement call. A dominated configuration needs none: there is no scenario in
which you would pick it. Eliminating them shrinks a seven-row table to the two
or three rows that genuinely trade off — which is where your recommendation
actually lives.

**The trap.** Domination is only as meaningful as the axes you checked. A
configuration dominated on quality/cost/latency may still win on, say,
explainability. Say which axes you used.

---

## Putting it together: the claim you are allowed to make

```
1. Measure both configurations on the same dev items.
2. Report each with its Wilson interval.            <- how precisely you know each
3. Run the paired test.  Report b, c, p.            <- whether they differ
4. If p >= 0.05: say "no detectable difference"     <- and decide on cost
   and choose on the other two axes.
5. If p < 0.05: say which is better, by how much,
   and at what cost and latency.
```

**The one sentence to take away.** *No number, no claim* has a sibling in this
lab: **no interval, no difference.**
