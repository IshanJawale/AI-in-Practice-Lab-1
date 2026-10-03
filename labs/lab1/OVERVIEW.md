# Lab 1 in plain language — what you are doing, and why

*Read this before `README.md`. It is the map; the README is the terrain.*

> Keep [`CONCEPTS.md`](CONCEPTS.md) open beside your editor while you work —
> every concept the lab uses, what it is, where it sits in the code, and
> where it came from in the theory.

---

## The one-sentence version

**Turn 240 genuinely messy support tickets into validated structured records —
and discover that the fields you take *away* from the model are the ones that
reach 100%.**

---

## Why this lab exists

Aurora Health Insurance gets about 10,000 support messages a day. A team of
agents reads each one and types a category and an urgency into a routing tool.
Forty seconds per ticket.

You have been asked to replace the typing.

That sounds like a prompting problem. It is not. It is a **systems** problem
that happens to have a model inside it, and this lab is where that stops being a
slogan.

### The two ideas the whole lab turns on

**1 · A model is a fast, cheap, occasionally-wrong function.** Everything of
value is the system you build around it. Your job is not to find magic words —
it is to decide what the model is allowed to decide, and to make everything else
impossible.

**2 · "It parsed" and "it is correct" are completely different guarantees.** You
will build something that *always* produces a well-formed record — 100% of the
time, no crashes, no malformed payloads — while being wrong about a third of the
records. Production needs the first guarantee absolutely, and it is not the same
as the second.

---

## The scope, in three pictures

### 1 · What goes in

Real-shaped tickets. Forwarded email chains with quoted history. WhatsApp
messages. HTML fragments from a web form. Hindi-English code-mixing. Typos.
Shouting. Signature blocks with phone numbers in them. **Some have no policy
number. Some have two, and they disagree.**

### 2 · What comes out

One validated record per ticket, with eight fields:

```
category · urgency · sentiment · product · language
policy_number · contains_pii · escalate
```

### 3 · What you are measured on

Three axes at once, never one:

```
        quality  ×  cost  ×  latency
```

| Metric | Target | Reference |
|---|---|---|
| Schema validity | **100%** | 1.000 |
| Field accuracy | ≥ 0.90 | 0.930 |
| Record accuracy (all 8 right) | ≥ 0.55 | 0.608 |
| Cost, 120-ticket run | ≤ $0.15 | $0.080 |
| p95 latency | ≤ 4,000 ms | 2,276 ms |
| Unhandled exceptions | **0** | 0 |

**Why record accuracy looks so bad.** All eight fields must be right at once.
The three judgement fields land at roughly 0.92 × 0.83 × 0.75 ≈ 0.57. Field
accuracy is the number engineers report; record accuracy is the number the
business feels. **The gap between them is the whole point** — do not close it by
quietly reporting only the first one.

---

## The steps: why, what, how

### Part A — Watch it break (35 min)

**Why.** You cannot engineer against failures you have not seen. Everyone
writes the naive version first; almost nobody looks carefully at *how* it fails.

**What.** Run the naive extractor. **Do not fix it.** Characterise it.

**How.**
```bash
python labs/lab1/v0_naive.py --n 40
```

The output comes in two halves.

**Part 1 — what v0 actually did.** It asks the model for JSON and calls
`json.loads`. Expect **0 out of 40 parsed**, with every failure in one bucket:
`markdown_fence`.

That is *correct*, not a broken key. The model is chat-tuned: in a chat window,
the right way to present JSON is inside a ```json code fence. So it does that,
every single time. **The bug is not the model's — it is v0's assumption that a
chat endpoint is a JSON API.** It isn't.

**Part 2 — what was hiding behind it.** Strip the fence and all 40 parse. But
look inside:

```json
{ "category": "Billing/Refund", "urgency": "High", "product": "Maternity Insurance" }
```

`category` is not one of your six values. `urgency` is a string, not a 1–5
integer. Every one of those is a separate failure — and **none of them were
counted**, because `json.loads` threw before the checks could run.

**The lesson is the arc:** `0/40 parsed → 40/40 parsed after a one-line fix →
still 0/40 clean.`

Someone will say "just strip the backticks". They are right, and it buys them
nothing. **One trivial bug was masking seven more serious ones.** That is why
Part B exists.

Now map each failure onto the **nine-failure taxonomy in T1 §3**, and note that
two rows in the table do not fit it. Rows that score **zero are findings too** —
write the zero down and say what it tells you about this model.

### Part B — Schema, validation, repair (45 min)

**Why.** If the model can emit an illegal value, it eventually will. The fix is
not a sterner prompt. It is a **contract** the output must satisfy, plus a loop
that repairs violations.

**What.** A Pydantic schema, wired to `aip.llm.structured`, that never crashes.

**How — four moves.**

**B1 · Design the schema.** `category` becomes a `Literal` over six values, not
a `str`. `urgency` becomes an `int` bounded 1–5.

Then the part people underestimate: **the `description=` text is shipped to the
model.** It goes into the JSON Schema and travels with every call. It is not
documentation for a human — it is the prompt, sitting right next to the thing it
governs, which is exactly where **T2 §3.2** says to put it.

Be concrete. "How urgent it is" is not a definition; the model will invent a
scale and it will not be yours. Anchor points 1, 3 and 5 with real situations.

> Publishing a proper urgency scale was worth **+0.067** on that field
> (0.683 → 0.750) with **no change to the model or the code.**

**B1a · Where does `evidence` go — first or last?** Not arbitrary. Pydantic
keeps declaration order, and the model is autoregressive: it is conditioned by
what it has already written. **Evidence first** makes it find its justification
*before* committing to a label. Evidence last lets it rationalise a label it
already chose. That is **T2 §3.3**. Either answer earns marks *if you state the
mechanism*; "it looked tidier" does not.

**B2 · Write the system prompt** using the seven-component structure from
**T2 §2**. It should be **shorter than your instinct** — most of what you want
to say belongs in the field descriptions.

**B3 · Wire up `aip.llm.structured`.** Read it first. It gives you JSON mode,
tolerant parsing, validation, and the repair loop — sending the validation
errors *back to the model* and asking it to fix them (**T2 §4.1**). You are
responsible for knowing what it does on your behalf.

**B4 · Never crash.** Catch the failure and return a record with
`needs_human_review=True`. This function must not raise. Ever.

```bash
python labs/lab1/run_eval.py --split dev --variant b
```

> **Checkpoint.** Validity **1.00**, field accuracy above **0.85**.
> If validity is below 1.00, that is your **exception handling**, not your
> prompt.
>
> **The bug that costs the most marks:** catching the exception but forgetting to
> set `needs_human_review=True`. Validity reads 1.00 and the record is empty.
> Nothing complains. If your numbers look suspiciously good, go find a failing
> case and look at it.

### Part C — Move work out of the model (30 min)

**Why.** The model is currently deciding all eight fields. Three of them are not
a judgement call at all. A policy number is `AUR-` followed by seven digits —
that is a regex, and a regex is free, instant, auditable, and **never wrong**.

This is **T1 §1.3**, the boundary rule, in the flesh.

**What.** Take the deterministic fields away from the model.

**How.**
- **C1** — `policy_number` by regex, `contains_pii` by pattern, `escalate` as a
  business rule in code where a compliance officer can read it.
- **C2** — **delete those fields from the schema the model sees.** Not just stop
  reading them — delete them. Shorter prompt, fewer output tokens.
- **C3 — the trap.** Some tickets contain **two** policy-number-shaped strings:
  one in the live message, one in a quoted reply below a `>` line, from an older
  ticket. They are not the same number. Decide a rule, **write it down**, and
  then ask yourself honestly whether it generalises or whether you have just
  fitted it to this dataset. Saying "I fitted it" is worth marks.

```bash
python labs/lab1/run_eval.py --split dev --variant c --compare b
```

> **Checkpoint — and read this carefully, because it is not what you expect.**
>
> **Cost falls. Accuracy holds. It does not rise.**
>
> Cost drops 20–25% ($0.052 → $0.040 on the reference). Field accuracy moves
> about **−0.02**, which is well inside noise (paired test **p = 0.45**).
>
> **Do not go hunting for a bug.** `policy_number`, `product` and `language`
> were *already at 1.000 in Part B* — the model was getting them right, so there
> were never any points there to win.
>
> What you bought is that those fields are now **guaranteed and auditable**
> instead of **usually right**, at lower cost. That is a completely different
> kind of win, and it is the one that matters in production.
>
> If cost did *not* fall, you removed the fields from the *output* but not from
> the *schema*. The model is still being asked for them.

### Part D — Measure and analyse (35 min)

**Why.** A number without analysis is a number nobody can act on.

**How.**
1. **Run the test split once.** Once. Iterating on test is how you fool
   yourself.
2. **Report the triple** — quality, cost, latency. Not one of them.
3. **Per-field breakdown.** Which field is worst? *It will not be the one you
   expect.* The reference lands at `urgency` 0.750, `sentiment` 0.833,
   `category` 0.917 — and **1.000 on all four deterministic fields.** That table
   is the lesson of the lab in one image.
4. **Read 15 failures.** Actually read them. Cluster them. Name your top three
   and say what you would do about each. Naming them correctly is the skill;
   you do not have to implement the fixes.
5. **The economic question.** Your measured cost per ticket × 10,000 tickets/day
   × 365. Against 40 seconds of agent time at ₹300/hour. **Below what record
   accuracy does this system stop being worth deploying?** Show the arithmetic.

That last one is **T1 §2.3**, and it is the moment the job stops looking like
prompt-writing.

---

## How this connects to the theory

| Theory | Where it shows up |
|---|---|
| **T1 §1.3 — the boundary rule** | Part C, entire. The four fields you move out reach 1.000 |
| **T1 §2.1 — tokens** | Part C: a shorter schema is fewer output tokens is less money |
| **T1 §2.2 — latency** | The p95 column. Averages hide the tail; the tail is what users feel |
| **T1 §2.3 — money** | Part D5, the annual-cost argument |
| **T1 §2.4 — reliability** | Part B4. Zero unhandled exceptions across 120 tickets |
| **T1 §3 — the nine failures** | Part A. You will personally produce #5 and #6 |
| **T1 §4 — architecture** | `extract.py` *is* layers 3–6; `aip/` is 1–2 |
| **T2 §2 — the prompt as a program** | B2, the seven-component system prompt |
| **T2 §3.1 — four levels of enforcement** | v0 is level 0. Part B is level 3 |
| **T2 §3.2 — designing the schema** | B1. Descriptions are shipped to the model |
| **T2 §3.3 — the evidence field** | B1a. Field order changes the answer, not just the layout |
| **T2 §4.1 — the repair loop** | B3, inside `aip.llm.structured` |
| **T2 §4.3 — don't ask for confidence** | Why the cascade trigger in Lab 2 is behavioural, not self-reported |

**The sentence that carries this lab and every one after it:**

> ### No number, no claim.

---

## What you are graded on

| Criterion | Weight | Full marks |
|---|---|---|
| Correctness | 25% | Meets accuracy and validity targets on test |
| Reliability engineering | 20% | Zero crashes; repair loop works; failures degrade to review, not exceptions |
| Boundary design | 20% | Deterministic fields moved out, **with the reasoning stated** |
| Measurement | 20% | All three axes; test run exactly once; dev/test gap acknowledged |
| Analysis | 15% | Error clusters specific and real; economic argument holds up |

**A negative result, honestly reported, scores full marks in the Analysis row.**
Your report must include **one thing you tried that did not work**, and why you
think it failed.

Fabricated or unreproducible numbers score **zero** for the lab.

---

## Before you start

- [ ] `make check` ends with `Environment is ready for Labs 1 and 2.`
- [ ] `make primer` prints **8/8 passing** — this lab is built on Pydantic, and
      meeting it for the first time in the room costs you the whole session
- [ ] `make tickets`, and **three things you noticed** written down
- [ ] `data/README.md` — the **annotation guidelines**. Not optional. These are
      the rules the labels came from, and **a label you cannot derive from a
      written rule is a label nobody can hit.** The *Known limitations* section
      is worth five minutes: two fields in this dataset were rewritten after a
      working solution was measured against them and the labels turned out to be
      unachievable.

## A note on providers

Every number above was measured on **Gemini** — use it if you can.
`AIP_PROFILE=nvidia` works too, but the published targets are Gemini's, so treat
it as the fallback rather than the reference.
