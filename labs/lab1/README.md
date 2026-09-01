# Lab 1 — The Reliable Extractor
**3 hours · Individual · Prepared by T1 and T2**

> **In the lab, follow [`RUNSHEET.md`](RUNSHEET.md).** It is the step-by-step
> flow: what to do, where to do it, and how you know each step is finished.
>
> **This file is the reasoning** — why each step exists and what it is teaching.
> Read it before the lab; keep the runsheet open during it.

---

## The problem

Aurora Health Insurance receives about 10,000 support messages a day across
email, WhatsApp, and an in-app form. Right now a team of agents reads each one
and types a category and an urgency into a routing tool. It takes about
40 seconds per ticket.

You have been asked to replace the typing.

You are given 240 real-shaped tickets: forwarded email chains with quoted
history, WhatsApp messages, HTML fragments from a web form, Hinglish
code-mixing, typos, shouting, and signature blocks containing phone numbers.
Some have no policy number. Some have two.

**Build a system that turns each ticket into a validated structured record.**

### Targets on the 120-item test split

| Metric | Target | Reference solution | Notes |
|---|---|---|---|
| Schema validity | **100%** | 1.000 | Non-negotiable |
| Field accuracy | ≥ 0.90 | 0.930 | |
| Record accuracy (all 8 fields correct) | ≥ 0.55 | 0.608 | Brutal by construction — see below |
| Total cost, full 120-item run | ≤ $0.15 | $0.080 | |
| p95 latency per ticket | ≤ 4,000 ms | 2,276 ms | |
| Unhandled exceptions | 0 | 0 | |

The "reference solution" column is measured, not estimated: it is a completed
Part C on the `SMALL` tier, run once on the test split. You are expected to get
close to it. Beating it is possible and the stretch goals are where to try.

**Why record accuracy looks so low.** Eight fields must *all* be right. Four of
them (`policy_number`, `contains_pii`, `product`, `language`) reach 1.000 once
you do Part C, so record accuracy is driven almost entirely by the three
judgement fields: roughly 0.92 × 0.75 × 0.83 ≈ 0.57. This is T3 §3.1 in the
flesh — field accuracy is the engineering metric, record accuracy is the one
the business feels, and the gap between them is the whole point.

Before you start, read `data/README.md`. It contains the **annotation
guidelines** the labels were produced from. This is not a hint sheet — it is
what every real labelling project ships, and a label you cannot derive from a
written rule is a label nobody can hit. Two of the fields in that document were
rewritten after a reference solution was measured against them and found the
labels unachievable; that story is in the "Known limitations" section and is
worth five minutes.

The validity target is the interesting one. 100% validity does **not** mean the
model is always right. It means your system always emits something well-formed —
possibly a record flagged for human review, but never a crash and never a
malformed payload. Those are different guarantees, and production needs the
second one absolutely.

---

## Timetable

| Time | Part | What you do |
|---|---|---|
| 0:00–0:10 | Setup | `make check`, and a show of hands on the primer |
| 0:10–0:45 | **A** | Build v0 the naive way. Watch it break. Record how |
| 0:45–1:30 | **B** | Schema + validation + repair loop |
| 1:30–2:00 | **C** | Move the deterministic fields out of the model |
| 2:00–2:35 | **D** | Run on test, measure the triple, error analysis |
| 2:35–3:00 | Show & tell | 4 minutes each: your table and your worst failure |

---

## Before the lab — four things, about an hour

None of this needs an API key except item 1, and none of it costs money. Doing
it beforehand is the difference between spending the three hours on the actual
problem and spending the first hour on setup.

### 1 · Your environment works — 5 min

```bash
make check
```

You are ready when the last line reads `Environment is ready.` If it does not,
fix it now, not on the day: see [`PRE_MODULE_SETUP.md`](../../PRE_MODULE_SETUP.md).

While you are there, spend thirty seconds on:

```bash
python scripts/check_rate_limit.py
```

This lab makes roughly **500 model calls** — about 2.8 per minute on average,
but bursty: a 120-item evaluation at 4 workers runs flat out for a couple of
minutes. The probe tells you whether your key can take that, and which
`--workers` value to use. Rate-limited calls are retried automatically, so a
tight key means slow, not broken.

### 2 · Pydantic — 30 min, and this one is not optional

This lab is built on Pydantic. If you meet it for the first time during the lab
you will spend all three hours fighting syntax instead of doing the work.

```bash
python labs/lab1/pydantic_primer.py
```

Eight exercises covering the exact surface this lab uses — `BaseModel`, `Field`
constraints, `Literal`, optional fields, `field_validator`, `ValidationError`,
and the three `model_*` methods. Nothing else. **You are ready when it prints
`8/8 passing`.**

Stuck on one? `python labs/lab1/pydantic_primer.py --solutions`. Reading an
answer and understanding it is fine. Skipping the file is not.

### 3 · Read five tickets — 10 min

You cannot design a schema for text you have not looked at.

```bash
python -c "
import json,random
rows=[json.loads(l) for l in open('data/eval/extraction_dev.jsonl')]
for r in random.sample(rows,5):
    print('='*70); print(r['expected']); print('-'*70); print(r['input'])
"
```

**Write down three things you notice that will make this hard.** You will be
asked for them in the first ten minutes.

### 4 · Read the annotation guidelines — 15 min

[`data/README.md`](../../data/README.md), the *Annotation guidelines* section.

These are the rules the labels were produced from. They are published for the
same reason every real labelling project publishes its guide: **a label you
cannot derive from a written rule is a label nobody can hit.** Pay attention to
the `urgency` scale and to the `complaint` boundary — that is where most of the
errors will be.

The *Known limitations* section at the end is worth five minutes too. Two of
the fields in that dataset were rewritten after a reference solution was
measured against them and found the labels unachievable.

---

## Part A — v0, the naive way (30 min)

Open `labs/lab1/v0_naive.py`. It is the version everyone writes first: a
prompt asking for JSON, `json.loads`, done.

```bash
python labs/lab1/v0_naive.py --n 40
```

**Your job is not to fix it. Your job is to characterise how it fails.** Fill in
this table in your report:

| Failure mode | Count in 40 | Example ticket id |
|---|---|---|
| Not valid JSON at all | | |
| JSON wrapped in a markdown fence | | |
| Extra prose before or after the JSON | | |
| Valid JSON, missing a required field | | |
| Valid JSON, category outside the allowed set | | |
| Urgency as a string instead of an int | | |
| Policy number invented (not present in the text) | | |
| Unhandled exception | | |

The script reports in two halves, and the second one is the point. **Part 1**
is what v0 actually did: how many records `json.loads` accepted, and why it
refused the rest. **Part 2** is what was hiding behind that refusal — the
defects inside the JSON that you never got to see, because one trivial bug
stopped you at the door.

Fill in the table from both halves. Rows that score zero are still findings:
write the zero down and say what it tells you about this model.

Map each row to a numbered failure from T1 §3. Two rows in the table have no
entry in that taxonomy — which, and where do they belong?

> **Checkpoint.** **Do not expect a broad spread.** On the current `SMALL`
> model, Part 1 reports `markdown_fence` on close to 40 out of 40 — that is
> correct behaviour, not a broken key. It fences deterministically. Part 2 then
> shows `urgency_is_string` and `category_out_of_set` at a similar rate.
>
> You are done when you can state the arc: **0/40 parsed → 40/40 parsed after a
> one-line fix → still 0/40 clean.** That gap is why Part B exists.
>
> **A genuinely broken key** does not look like this — it raises exceptions and
> shows up under *unhandled exceptions* in Part 1, with `calls=0` in the budget
> line. If that is what you see, run `make check`.

---

## Part B — Schema, validation, repair (45 min)

Open `labs/lab1/extract.py`. Complete the four TODOs.

**B1. Design the schema.** `TicketRecord` is started for you with two fields.
Add the rest. Requirements:

- `category` must be a `Literal` over the six allowed values, never `str`.
- `urgency` must be an `int` constrained to 1–5, with a `description` that
  actually defines the scale. "How urgent it is" is not a definition; the model
  will invent its own scale and it will not be yours.
- `policy_number` must be `str | None` with `pattern=r"^AUR-\d{7}$"` and a
  description that explicitly says to return `null` when absent and never to
  invent or reformat one.
- `sentiment`, `product`, `contains_pii`, `language` per the gold labels in the
  data. Look at `expected` in the dev file for the exact allowed values.
- Add an `evidence: str` field capped at 200 characters, holding the span of the
  ticket that decided the category.

**Decide, and justify in a comment: does `evidence` go before or after
`category` in the class?** T2 §3.3 explains why the answer is not arbitrary.

**B2. Write the system prompt.** Use the seven-component structure from T2 §2.
Order it for both attention and prompt caching. It should be shorter than you
expect — most of your instructions belong in field `description`s, not in prose.

**B3. Wire up `aip.llm.structured`.** It gives you JSON mode, tolerant parsing,
Pydantic validation, and the repair loop. Read it first (`aip/llm.py`) — you
are responsible for knowing what it does on your behalf.

**B4. Never crash.** Catch `StructuredOutputError` and return a record with
`needs_human_review=True` rather than propagating. Add that field to the schema.

Then:

```bash
python labs/lab1/run_eval.py --split dev --variant b
```

> **Checkpoint.** Validity should be 1.00 and field accuracy above 0.85. If
> validity is below 1.00 your exception handling is wrong, not your prompt.

---

## Part C — Move work out of the model (30 min)

Right now the model is deciding all eight fields. Three of them should not be
its problem at all.

**C1.** Implement `extract_deterministic()`: `policy_number` by regex,
`contains_pii` by the patterns in `aip.guards.redact_pii`, and `escalate` as a
business rule in code.

**C2.** Remove those fields from the schema the model sees. Your prompt gets
shorter, output tokens drop, and three fields become 100% accurate and fully
auditable.

**C3.** Handle the trap: a few tickets contain *two* policy-number-shaped
strings — one in the body and one in a quoted reply from a previous ticket.
Decide a rule, write it down, and implement it. (Look at the gold labels to see
which one is correct, then ask yourself whether your rule generalises or
whether you have just fitted to the data.)

```bash
python labs/lab1/run_eval.py --split dev --variant c --compare b
```

> **Checkpoint.** **Cost falls. Accuracy holds — it does not rise, and that is
> the finding.**
>
> Cost should drop 20–25% (reference: $0.052 → $0.040 on dev). Two field
> descriptions left the prompt and two values left every response. If cost did
> *not* fall, you removed the fields from the *output* but not from the
> *schema* — the model is still being asked for them.
>
> Field accuracy moves by about −0.02 on the reference, which is well inside
> noise (paired test p = 0.45). Do not go looking for a bug. `policy_number`,
> `product` and `language` were **already at 1.000 in Part B** — there were no
> points there to win. What Part C buys is that those fields are now
> *guaranteed and auditable* rather than *usually right*, at lower cost.
>
> Say that in your report. If you expected an accuracy jump and did not get
> one, explaining why is worth more than the jump would have been.

---

## Part D — Measure and analyse (35 min)

**D1. Run the test split, once.**

```bash
python labs/lab1/run_eval.py --split test --variant c --save reports/lab1_test.json
```

**D2. Report the triple.** Quality × cost × latency. Not one of them.

**D3. Per-field breakdown.** Which field is worst? It will not be the one you
expected — the reference solution lands at `urgency` 0.75, `sentiment` 0.83,
`category` 0.92, and 1.00 on all four deterministic fields. Produce the
confusion matrix for `category`, and check whether your `urgency` errors are
off-by-one at a boundary (they will be) or scattered (they should not be).

**D4. Error analysis.** Open 15 failures and read them. Cluster them. Name your
top three clusters and, for each, state the fix you would make and roughly what
you think it is worth. You do not have to implement the fixes — naming them
correctly is the skill.

**D5. The economic question.** Using your measured cost per ticket, compute the
annual cost at 10,000 tickets/day. Compare against 40 seconds of agent time per
ticket at ₹300/hour. State the break-even accuracy: below what record accuracy
does this system stop being worth deploying? Show the arithmetic.

---

## Deliverables

Push to your repo under `labs/lab1/`:

1. `extract.py` — your working extractor
2. `report.md` — at most two pages:
   - the Part A failure table
   - the variant comparison table (v0 / B / C) with quality, cost, p95
   - per-field accuracy and the `category` confusion matrix
   - top three error clusters with proposed fixes
   - the D5 economic argument
   - **one thing you tried that did not work**, and your explanation of why
3. `reports/lab1_test.json` — the raw harness output

---

## Rubric (9% of Module 1)

| Criterion | Weight | Full marks means |
|---|---|---|
| Correctness | 25% | Meets the accuracy and validity targets on test |
| Reliability engineering | 20% | Zero crashes; repair loop works; failures degrade to review, not exceptions |
| Boundary design | 20% | Deterministic fields moved out of the model, with the reasoning stated |
| Measurement | 20% | All three axes reported; test split run exactly once; dev/test gap acknowledged |
| Analysis | 15% | Error clusters are specific and real; economic argument holds up |

**A negative result, honestly reported, scores full marks in the Analysis row.**
Fabricated or unreproducible numbers score zero for the lab.

---

## Stretch (if you finish early)

1. **Cascade.** Route to a larger model only when validation fails or the
   evidence field is empty. Report the blended cost and the escalation rate.
2. **Batch.** Extract 10 tickets in one call. Measure the cost saving and the
   accuracy cost. (There is one. Find it and explain it.)
3. **Self-consistency on `urgency`.** Sample 3 times at temperature 0.7, take
   the median. Does disagreement predict error? Plot it.
4. **Run the blind set** (`data/eval/extraction_blind.jsonl`) and submit your
   predictions. The instructor scores it. If your blind score is materially
   below your test score, that is worth understanding.
