# Lab 1 — Runsheet

**Follow this top to bottom.** Every step says what to do, where to do it, and
how you know you are finished.

This is the *action* layer. [`README.md`](README.md) is the *reasoning* layer —
why each step exists, and what it is teaching. Read the README before the lab;
keep this open during it.

**Keep a scratch file open from the start.** Several steps say *write this
down*, and those notes are your report.

---

## Before you sit down

- [ ] `make check` → `Environment is ready.`
- [ ] `python labs/lab1/pydantic_primer.py` → `8/8 passing`
- [ ] `make ratecheck` → note the `--workers` value it recommends
- [ ] Read five tickets, write down three things that will make this hard
- [ ] Skim `data/README.md` → *Annotation guidelines*

If any of these is not done, do it now. It is faster than debugging it later.

---

# 0 · Setup — 10 min

**0.1** Open three things and leave them open:

| | |
|---|---|
| edit | `labs/lab1/extract.py` |
| read | `data/README.md` (annotation guidelines) |
| scratch | a notes file for the report |

**0.2** Confirm the data is there:

```bash
python -c "import json; print(sum(1 for _ in open('data/eval/extraction_dev.jsonl')), 'dev cases')"
```

> **Done when:** it prints `60 dev cases`.

---

# 1 · Part A — watch it break — 35 min

You are not fixing anything here. You are characterising *how* a naive
extractor fails.

**1.1** Run the naive version:

```bash
python labs/lab1/v0_naive.py --n 40
```

**1.2** Fill in this table in your notes. The script prints most of it.

| Failure mode | Count in 40 | Example ticket id |
|---|---|---|
| Not valid JSON at all | | |
| JSON wrapped in a markdown fence | | |
| Extra prose before or after the JSON | | |
| Valid JSON, missing a required field | | |
| Category outside the allowed set | | |
| Urgency as a string instead of an int | | |
| Policy number invented (not in the text) | | |
| Unhandled exception | | |

**1.3** Against each row, write the number of the matching failure from
**T1 §3** (the nine-failure taxonomy).

**1.4** Answer in your notes: **two rows do not map cleanly onto that
taxonomy.** Which two, and where do they belong?

The script reports in two halves. **Part 1** is what v0 actually did. **Part 2**
is what was hiding behind it — the defects inside the JSON you never reached,
because one trivial bug stopped you at the door. Fill the table from both.

> **Done when:** every row is mapped, zeros included, and you can state the arc
> the script prints at the end: **0/40 parsed → 40/40 parsed after a one-line
> fix → still 0/40 clean.**
>
> **Almost everything in one bucket?** That is expected here. The current
> `SMALL` model fences every response, so `markdown_fence` lands at ~40/40 and
> Part 2 shows `urgency_is_string` and `category_out_of_set` at a similar rate.
> Rows that stay at zero are findings too — this model does not invent policy
> numbers or drop fields. Say so.
>
> **Broken key?** It does not look like this. It raises exceptions, lands under
> *unhandled exceptions*, and the budget line reads `calls=0`. Then run
> `make check`.

---

# 2 · Part B — the schema — 45 min

All edits are in `labs/lab1/extract.py`.

**2.1 — the schema.** Complete the TODOs in `class TicketRecord`, in order:

| TODO | Field | What it needs |
|---|---|---|
| `B1a` | `evidence` placement | Decide **before or after** `category`. Leave a one-line comment saying which effect you chose. T2 §3.3 |
| `B1b` | `category` | Define each of the six values in one clause. Watch the `complaint` boundary |
| `B1c` | `urgency` | Define the 1–5 scale concretely. Anchor points 1, 3 and 5 |
| `B1d` | `sentiment` | `Literal["angry","frustrated","neutral","satisfied"]` |
| `B1e` | `product` | `Literal["bronze","silver","gold","platinum","unknown"]` |
| `B1f` | `language` | `Literal["en","hi-en"]` |
| `B1g` | `evidence` | `str`, `max_length=200`, with a description |
| `B1h` | `policy_number` | Exact format, and **explicitly** say null when absent |
| `B1i` | `contains_pii` | Description |
| `B1j` | validator | Reject anything not exactly `AUR-` + 7 digits |

> The scale definitions for `urgency` and the `category` boundaries are in
> `data/README.md`. Use them — they are the rules the labels were made from.

**2.2 — `TODO B2`.** Write `SYSTEM_PROMPT` using the seven-component structure
from T2 §2. Order it stable-first, volatile-last.

> It should be **shorter than you expect**. Most of your instructions belong in
> the field `description`s, not in prose.

**2.3 — `TODO B3`.** Wire `extract_b()` to `aip.llm.structured`.

**2.4 — `TODO B4`.** Catch `StructuredOutputError` and return a record with
`needs_human_review=True`. **This function must never raise.**

**2.5** Run it:

```bash
python labs/lab1/run_eval.py --split dev --variant b
```

> **Done when:** `schema_valid` is **1.000** and `field_accuracy` is above **0.85**.
>
> **Validity below 1.000?** That is your exception handling, not your prompt.
> Every failure path must return a record.
> **Suspiciously good?** Ask to see a failing case — if `needs_human_review` is
> never set, step 2.4 is incomplete.

---

# 3 · Part C — move work out of the model — 30 min

**3.1 — `TODO C1`.** Implement `extract_deterministic()`: `policy_number` by
regex, `contains_pii` from the patterns in `aip.guards`.

**3.2 — `TODO C3`, the trap.** Some tickets contain **two** policy-number-shaped
strings — one in the live body, one in a quoted reply below a `>` line. Decide a
rule, **write it down in a comment**, and implement it.

> Then ask yourself in your notes: does your rule generalise, or have you fitted
> it to this dataset? The honest answer is worth marks.

**3.3 — `TODO C1b`.** Implement `apply_business_rules()` — `escalate` in code:

```python
escalate = urgency >= 4 or "ombudsman" in ticket.lower()
```

**3.4 — `TODO C2`.** Build `TicketRecordC`: copy `TicketRecord` and **delete the
fields you now compute in code.** The model must no longer see them.

**3.5** Complete `extract_c()` — model fields + deterministic fields + business
rules, returned as a plain dict.

**3.6** Compare against Part B:

```bash
python labs/lab1/run_eval.py --split dev --variant c --compare b
```

> **Done when:** cost is **down** and accuracy **holds**.
>
> Reference on dev: cost $0.052 → $0.040 (−23%), field accuracy 0.945 → 0.929.
> That −0.017 is noise (p = 0.45), not a regression, and not a bug to hunt.
> Accuracy was never the prize here: `policy_number`, `product` and `language`
> were already at 1.000 in Part B.
>
> **Cost did not fall?** You removed the fields from the *output* but not from
> the *schema*. The model is still being asked for them.

**3.7** Write down, for your report: which fields reached **1.000**, and what
they were before.

---

# 4 · Part D — measure and analyse — 35 min

**4.1 — run the test split. Once.**

```bash
python labs/lab1/run_eval.py --split test --variant c --save reports/lab1_test.json
```

> **Once.** Iterating against test means fitting to it, and your number stops
> meaning anything. T3 §2.4.

**4.2** Record the **triple** — quality × cost × latency. Not one of them.

**4.3** Per-field breakdown and the `category` confusion matrix. Both are
printed by the command above.

> Write down which field is worst. It will not be the one you expected.

**4.4 — error analysis.** Open **15 failures** and read them. Cluster them.
Name your **top three clusters** with counts, and for each, the fix you would
make and roughly what you think it is worth.

> You do not have to implement the fixes. Naming them correctly is the skill.

**4.5 — the economic argument.** Using your measured cost per ticket:

- annual cost at 10,000 tickets/day
- versus 40 seconds of agent time per ticket at ₹300/hour
- **the break-even record accuracy** — below what number does this stop being
  worth deploying?

Show the arithmetic.

---

# 5 · Deliverables — push before show & tell

```
labs/lab1/extract.py          your working extractor
labs/lab1/report.md           at most two pages
reports/lab1_test.json        raw harness output
```

`report.md` must contain:

- [ ] the Part A failure table
- [ ] variant comparison: v0 / B / C, with quality **and** cost **and** p95
- [ ] per-field accuracy and the `category` confusion matrix
- [ ] top three error clusters with proposed fixes
- [ ] the 4.5 economic argument, with arithmetic
- [ ] **one thing you tried that did not work**, and why you think it failed

> The last one is not optional and it is not a penalty. An honest negative
> result scores full marks.

---

# 6 · Show & tell — 4 minutes

1. Your comparison table, on screen (1 min)
2. What moving fields out of the model bought you — accuracy, cost, latency (1 min)
3. Your worst remaining failure, and what you would do about it (1 min)
4. Questions (1 min)

---

## Targets — what you are aiming at

| Metric | Target | Reference solution |
|---|---|---|
| Schema validity | **1.00** | 1.000 |
| Field accuracy | ≥ 0.90 | 0.930 |
| Record accuracy | ≥ 0.55 | 0.608 |
| Cost, full 120-item run | ≤ $0.15 | $0.080 |
| p95 latency | ≤ 4,000 ms | 2,276 ms |
| Unhandled exceptions | 0 | 0 |

The reference column is **measured**, not estimated. Getting close is the job;
beating it is what the stretch goals are for.

*On the `nvidia` profile these numbers are lower — field 0.881, record 0.400.
Quote your own baseline and say which provider you used.*

---

## If you are running behind

Triage in this order. It is better to finish Part C properly than to rush all four.

| Time | If you are here | Do this |
|---|---|---|
| 1:30 | still in Part B | Take the schema from a neighbour, keep your own prompt, move to Part C. **Part C is where the lesson is.** |
| 2:00 | Part C not done | Skip C3 (the two-policy trap). Do 3.3–3.6 |
| 2:35 | Part D not done | Run 4.1 and record the triple. Do the error analysis as homework |

Never skip: **step 2.4** (never crash), **step 3.6** (the comparison), and
**step 4.1** (the test run).

---

## Stuck?

| Symptom | Look at |
|---|---|
| `StructuredOutputError` on most tickets | `max_tokens` too low, or your schema is too large. Check `finish_reason` |
| Validity below 1.000 | Step 2.4 — a failure path is raising instead of returning |
| Accuracy stuck around 0.5 on `urgency` | You have not used the published scale. `data/README.md` |
| Cost is zero | You are on an unpriced model, or every call is cached. `make cost` |
| 429s | Lower `--workers`. Rate-limited calls retry automatically — it is slow, not broken |

**Ten-minute rule:** if you are stuck on something that is not the lab's
subject — an installer, a path, an import — ask immediately. That is not what
is being assessed.
