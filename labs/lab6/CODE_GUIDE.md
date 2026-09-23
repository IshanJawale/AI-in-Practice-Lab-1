# Lab 6 — the code: what is provided, and every TODO

Two files: **`agent.py`** (the tool loop) and **`redteam.py`** (the attacks).
Most of the defensive machinery already exists in `aip/guards.py` — this lab is
largely about **wiring it up and measuring what each piece buys.**

> `aip/` is the toolkit — read it, never change it. `labs/` is your system.

---

## What you will call from `aip/`

| You need | It lives in | Signature |
|---|---|---|
| The tool-call gate | `aip.guards` | `ToolGuard(max_calls=8, allow=set(), requires_confirmation=set(), confirm_fn=None)` |
| Execute one tool through the gate | `aip.guards` | `guard.call(name, args, registry, schemas=None)` |
| The denial it raises | `aip.guards` | `ToolDenied` |
| Layer 1 — fence off untrusted text | `aip.guards` | `delimit_untrusted(content, label="RETRIEVED_DOCUMENT")` |
| Layer 2 — heuristic detector | `aip.guards` | `detect_injection(text) -> InjectionVerdict` |
| Layer 5 — output filtering | `aip.guards` | `redact_pii(text)`, `_PII_PATTERNS` |
| Layer 3 — structured answers | `aip.llm` | `structured(prompt, schema=..., ...)` |
| Tool-calling chat | `aip.llm` | `chat(..., tools=..., tool_choice=..., return_full=True)` |
| Spend ceiling — termination condition 3 | `aip.cost` | `Budget(limit_usd=..., label=...)` |
| The `search_policy` backend | `aip.retrieval` | your Lab 3 configuration |

**`ToolGuard.call` fires its controls in order:** allowlist → registry → call
budget → argument schema → confirmation → execute. Everything is appended to
`guard.log`, which is where your D1 numbers come from.

---

## `agent.py` — the loop

### Provided

**Four argument schemas** — `SearchArgs`, `PolicyArgs`, `PremiumArgs`,
`RefundArgs`. Read `RefundArgs` closely; it is the answer to **B4**:

```python
policy_number: str = Field(pattern=r"^AUR-\d{7}$")
amount_inr:    int = Field(gt=0, le=50_000)
reason:        str = Field(min_length=10, max_length=500)
```

**Four tool functions** and `tool_specs()`, which renders them as JSON schemas
for the model.

> **`search_policy` has a TODO marked D1** on purpose: it returns raw corpus
> text **straight into the model's context**. That is the hole layer 1 closes.

### `SYSTEM` — **TODO A1**

The system prompt. It must establish that retrieved text is *data, not
instructions* — that clause is half of layer 1.

### `run_agent(question, *, guard=None, ...)` — **TODO A1–A3**

The loop: model call with tool schemas → execute requested tools → feed results
back → repeat until it answers or a budget stops it.

**Three termination conditions, each tested separately (A2):** max tool calls,
max wall-clock, max spend.

> A denied tool must come back **to the model as a result it can act on** —
> "that tool is not available to you" — not as an exception that kills the loop.
> A crash is a worse outcome than a refusal.

---

## `redteam.py` — the attacks

### `load_suite()` — provided

Reads `data/attacks/attack_suite.jsonl`: **21 cases — 17 real attacks and 4
controls.** The controls are the point. A guard that blocks everything is not a
guard.

### `inject_documents(cases)` — **TODO**

Copy `data/corpus/` to a temp dir and add the `indirect_document` payloads, so
the indirect attacks `I01`–`I05` are actually *in the corpus*. **If you skip
this, those five silently never fire** and your block rate is meaningless.

### `attack_succeeded(case, result)` — **TODO C1**

**Write this before you run anything.** Deciding what "success" means *after*
seeing the output is how you talk yourself into a good score.

Be specific per case — for `I01`, success means the answer mentions Vertex
Insurance.

### Runners — provided

| Command | What it does |
|---|---|
| `--no-guards` | the unguarded baseline (Part C) |
| `--layers 1 2 3` | enable specific defence layers (Part D) |
| `--save` | persist results for the D1 table |

---

## The five layers, and where each lives

| # | Layer | Implementation |
|---|---|---|
| 1 | Delimit + declare | `delimit_untrusted()` around retrieved text **plus** the system clause. Both halves, or neither works |
| 2 | Heuristic detector | `detect_injection()` on retrieved content. **This is the one with the false-positive cost** — see `C02` |
| 3 | Structured output | `aip.llm.structured` with a schema. Large win, no false positives: an injected instruction has nowhere to go in a typed object |
| 4 | Privilege capping | `ToolGuard(allow=..., requires_confirmation={"issue_refund"})`. Does not stop injection — **turns a breach into a quality incident** |
| 5 | Output filtering | Scan the answer for leaked prompt text, URLs and PII before returning |

---

## The traps

1. **Skipping `inject_documents`.** Five attacks silently never fire.
2. **Writing success criteria after seeing the output.**
3. **Measuring block rate without false positives.** Blocking everything scores
   1.00 and is worthless.
4. **Letting `ToolDenied` escape.** Return it to the model.
5. **Treating layer 4 as prevention.** It is containment — and containment is
   what makes a breach survivable.

## Common errors

| Symptom | Cause |
|---|---|
| `NotImplementedError` | One of the four TODOs |
| The loop never terminates | A2/A3 — no budget wired in |
| Indirect attacks all "blocked" | They never ran. Check `inject_documents` |
| `ToolDenied` crashes the run | Catch it, return it to the model as a result |
| False positives 4/4 | Your detector is matching on surface strings. See `C02` |
| Cost above $0.02/query | The loop is making more calls than it needs; cap `max_calls` |
