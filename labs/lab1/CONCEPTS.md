# Lab 1 — Concepts
### Keep this open while you work

Every concept the lab uses: what it is, **where it is in the code**, and where
it came from in the theory. [`OVERVIEW.md`](OVERVIEW.md) is the orientation;
[`RUNSHEET.md`](RUNSHEET.md) is the steps; this is the reference.

| Concept | In the code | In the theory |
|---|---|---|
| The model/code boundary | `extract.py::extract_c` | T1 §1.3 |
| Four levels of enforcement | your schema | T2 §3.1 |
| JSON mode | `aip/llm.py::structured` | T2 §3.1 |
| JSON Schema as the instruction | `aip/llm.py:286` | T2 §3.2 |
| Pydantic contracts | `TicketRecord` | T2 §3 |
| `field_validator(mode=…)` | `TODO B1j` | — primer ex. 5 |
| Tolerant parsing | `aip/llm.py::extract_json` | T1 §3 #5 |
| The repair loop | `aip/llm.py::structured` | T2 §4.1 |
| Truncation | `finish_reason` | T1 §3 #4 |
| Graceful degradation | `TODO B4` | T1 §2.4 |
| Field vs record accuracy | `aip/evals.py::field_accuracy` | T3 §3.1 |
| The triple | `Budget.report()` | T1 §2, T3 §3.2 |
| Split discipline | `run_eval.py --split` | T3 §2.4 |
| Unit economics | your D5 arithmetic | T1 §2.3 |

---

## The model/code boundary

**What it is.** For each field, ask: *is this a judgement, or a rule?* Rules go
in code, where they are deterministic, auditable, unit-testable and free.
Judgements go to the model, because nothing else can make them.

**In the code.** `extract_deterministic()` and `apply_business_rules()` are the
code side; `TicketRecordC` is what is left for the model.

**In the theory.** T1 §1.3 — the rule the whole module is built on.

**The trap.** Moving a field into code guarantees 1.000 only when its inputs are
*in the text*. `escalate` is computed by a deterministic rule and still scores
0.933, because its input `urgency` is a model prediction. Determinism protects
everything downstream of a decision; it cannot repair the decision.

---

## The four levels of enforcement

**What it is.** Four ascending ways to make the model do something:

| Level | Mechanism | Strength |
|---|---|---|
| 1 | Prose in the prompt | A request |
| 2 | `Field(description=…)` | A request, attached to the thing it governs |
| 3 | Type / constraint (`Literal`, `ge`, `pattern`) | Enforced — violation raises |
| 4 | Computed in code | Guaranteed — the model is not consulted |

**In the code.** Part B moves you from level 1 to level 3; Part C moves four
fields to level 4.

**In the theory.** T2 §3.1.

**The trap.** Level 2 feels like level 3. It is not. A `str` field with the six
categories listed in its description accepts `"Billing Issue"` silently.

---

## JSON mode and the JSON Schema instruction

**What it is.** `response_format={"type":"json_object"}` asks the provider to
constrain decoding to valid JSON. It guarantees *syntax*, never *shape* — so
validation still happens after.

**In the code.** `aip/llm.py::structured` requests it, falls back to plain text
if the provider rejects it, and — the part that matters — serialises
`schema.model_json_schema()` into the system prompt. Read `llm.py:286`.

**In the theory.** T2 §3.1–3.2.

**The trap.** Because the schema is shipped, your `Field(description=…)` text
reaches the model *attached to its field*. A rule written 300 words earlier in
prose is the one that gets dropped. This is why your system prompt should come
out shorter than your instinct.

---

## `field_validator` and validation order

**What it is.** A hook that runs your own code during validation.
`mode="before"` runs on the raw input, ahead of type coercion and constraints.
`mode="after"` runs on the already-validated value.

**In the code.** `TODO B1j`, normalising `""` and `"null"` to `None` before the
`pattern` constraint sees them.

**In the theory.** Not in the lectures — it is primer exercise 5.

**The trap.** An `after` validator cannot rescue a value that failed the
constraint, because validation already raised. If you are normalising, you need
`before`.

---

## Tolerant parsing, and why it is not the fix

**What it is.** Recovering a JSON object from a response wrapped in markdown
fences or surrounded by prose.

**In the code.** `aip/llm.py::extract_json`. Part A's `salvage()` is the same
idea, written out so you can see it.

**In the theory.** T1 §3, failure #5.

**The trap.** This is the entire lesson of Part A. Tolerant parsing takes you
from 0/40 parsed to 40/40 parsed and leaves you at **0/40 clean**. It buys you
the right to *see* the defects; it removes none of them.

---

## The repair loop

**What it is.** On a validation failure, send the Pydantic errors **back to the
model** as a new message and ask it to fix its output. Bounded retries.

**In the code.** `aip/llm.py::structured`, the `for attempt in range(max_repairs
+ 1)` loop. Read it before you use it.

**In the theory.** T2 §4.1.

**The trap.** Repairs are not free. Every attempt goes through `raw_call`, so it
is cached, counted and billed. A high repair rate is a cost line you will see in
Part D — and usually a symptom of a schema that is too large or a `max_tokens`
that is too small.

---

## Truncation

**What it is.** The model stopped because it ran out of output budget, not
because it finished. `finish_reason == "length"`.

**In the code.** `structured()` treats it separately from a schema failure —
truncated JSON is not malformed JSON and must not be "repaired" as such; the
budget is doubled instead.

**In the theory.** T1 §3, failure #4.

**The trap.** Truncated prose looks *fine*. It is the one failure that produces
a plausible, complete-looking, silently incomplete answer — and Lab 4 will show
you it doing exactly that to this course's own evaluation harness.

---

## Graceful degradation

**What it is.** On failure, return something well-formed and flagged, rather
than propagating an exception.

**In the code.** `TODO B4` — catch `StructuredOutputError`, return a record with
`needs_human_review=True`. `extract_b` must never raise.

**In the theory.** T1 §2.4.

**The trap.** `schema_valid` measures *this*, not the model's accuracy. Anything
below 1.000 means a failure path escaped, and the fix is in your `except`, never
in your prompt.

---

## Field accuracy vs record accuracy

**What it is.** Field accuracy is the mean over all 8 fields on all items.
Record accuracy requires **all 8 fields simultaneously correct** on an item.

**In the code.** `aip/evals.py::field_accuracy` returns both.

**In the theory.** T3 §3.1.

**The trap.** They are the same measurement and they answer different questions.
0.930 field accuracy sits alongside 0.608 record accuracy because four fields at
1.000 leave the record score as roughly the product of the three judgement
fields (0.92 × 0.75 × 0.83). Field accuracy tells you where to work; record
accuracy is what the business feels. Report both.

---

## The triple, and unit economics

**What it is.** Quality, cost and latency are one measurement with three
components. A quality claim without the other two is not a result.

**In the code.** `Budget.report()` gives you cost and call counts; the harness
gives p50/p95.

**In the theory.** T1 §2 for the resources, T3 §3.2 for the reporting rule, and
T1 §2.3 for the arithmetic worked through end to end.

**How to do the D5 arithmetic.**

```
cost per ticket   = run cost / items in the run
cost per day      = cost per ticket x tickets per day
cost per year     = cost per day x 365
human cost/ticket = hourly rate x (seconds per ticket / 3600)
```

**The trap.** p95, not the mean. A mean of 900 ms with a p95 of 6 s is a system
that feels broken to one user in twenty, and the repair loop is what puts the
weight in that tail.

---

## Split discipline

**What it is.** `dev` (60) is for iterating. `test` (120) is run once, at the
end, on a candidate you have already chosen. `blind` (60) is unlabelled and
scored by the instructor.

**In the code.** `run_eval.py --split`, which prints a warning after a test run.

**In the theory.** T3 §2.4.

**The trap.** The moment you use test to *choose* between two systems, it has
become a dev set and its number is optimistic. If you do it, say so — disclosed
is Adequate, undisclosed is the module's only automatic zero.
