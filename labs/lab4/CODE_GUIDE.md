# Lab 4 — the code: what is provided, and every TODO

Two files are yours: **`rag.py`** (the answer pipeline) and **`evaluate.py`**
(the harness). Both lean on `aip/`, and knowing which side of that line a thing
lives on is most of the battle.

> **Rule of thumb for the whole module.** `aip/` is the toolkit: provider
> plumbing, metrics, guards. `labs/` is the system you are building. You may
> read anything in `aip/`; you may not change it — Labs 5–7 depend on it.

---

## What you will call from `aip/`

| You need | It lives in | Signature |
|---|---|---|
| Number the sources so citations are checkable | `aip.retrieval` | `format_context(hits, max_chars=8000) -> str` |
| Check `[n]` indices in an answer | `aip.guards` | `enforce_citations(answer, n_sources) -> (bool, list[int])` |
| A reference answer prompt (read **after** you write yours) | `aip.rag` | `ANSWER_SYSTEM` |
| A complete reference pipeline | `aip.rag` | `RagPipeline` |
| One judge call, JSON verdict | `aip.evals` | `llm_judge(prompt, tier="LARGE", max_tokens=2048) -> dict` |
| Starting rubrics — deliberately improvable | `aip.evals` | `JUDGE_RUBRIC_FAITHFULNESS`, `JUDGE_RUBRIC_CORRECTNESS` |
| Cohen's κ against your hand labels | `aip.evals` | `judge_agreement(judge, human) -> dict` |
| Structured generation with repair | `aip.llm` | `structured(prompt, schema=..., system=..., tier=...)` |
| Cost ceiling for a run | `aip.cost` | `Budget(limit_usd=..., label=...)` |

Two details that matter:

- **`llm_judge` defaults to `tier="LARGE"` on purpose** — a *different and
  stronger* tier than the system under test, because self-preference bias is
  real (T3 §4.1).
- **It returns `parse_error`** when the verdict will not parse. That is missing
  data. Do not score it 0.

---

## `rag.py` — the pipeline

### Provided

`Answer` — the dataclass your pipeline returns. Read its fields first; they
tell you what the rest of the lab expects you to produce.

### `ANSWER_SYSTEM` — **TODO A**

Write it **before** reading `aip/rag.py::ANSWER_SYSTEM`, then diff the two. Six
required elements are in the runsheet and in README Part A.

### `validate_answer(text, n_sources, finish_reason=None) -> dict` — **TODO B2**

Must establish:

| Check | Why |
|---|---|
| every `[n]` is in range | a citation you never supplied is a *provable* hallucination |
| non-empty, and `finish_reason != "length"` | a truncated answer looks fine and is silently incomplete (T1 failure 4) |
| at least one citation, unless it is a refusal | an uncited claim is unauditable |

`aip.guards.enforce_citations` does the index check; the rest is yours.

### `answer_question(question, retriever, *, k=12, ...)` — **TODO**

The pipeline: **retrieve → (rerank) → generate → validate → maybe repair.**

**B3 lives here:** what happens when validation fails? Retry with a corrective
message, strip the bad citation, or fall back to refusal. Pick one, *defend it
in a comment*, and never silently return a bad citation.

### `answer_with_gold_context(question, gold_docs, ...)` — **TODO E2**

**Same generator, different context** — the gold documents, chunked, with no
retrieval. That "same generator" is the entire point: change anything else and
the comparison is meaningless.

---

## `evaluate.py` — the harness

### `build_retriever()` — **TODO**

**Put your Lab 3 winning configuration here.** The placeholder is a placeholder.
Leaving it is throwing away Lab 3.

### `judge_faithfulness(answer_text, context) -> int` — **TODO D1**

Returns 0 or 1. Improve `JUDGE_RUBRIC_FAITHFULNESS` first — it is a starting
point, not an answer.

### `judge_correctness(question, candidate, reference) -> int` — **TODO D1**

Returns 0, 1 or 2. **Handle refusal explicitly:** if the reference says the
right behaviour is to refuse, a refusal scores full marks and a confident
answer scores zero. A rubric silent on that punishes correct behaviour.

### Provided runners

| Command | What it does |
|---|---|
| `--full --save reports/lab4.json` | every metric; **Lab 5 reads this file** |
| `--gold-context` | the E2 decomposition |
| `--calibrate` | writes the hand-labelling sheet for D2 |
| `--kappa` | computes κ once you have labelled it |

---

## The traps

1. **Judge truncation.** A reasoning judge spends most of its budget on
   invisible thinking. Cap it too low and the JSON truncates, fails to parse,
   and gets scored 0 — a silent downward bias. This cost the reference a
   faithfulness reading of 0.667 when the truth was 0.933.
2. **Scoring a parse failure as 0.** It is missing data. Exclude it, or retry.
3. **Reporting one refusal number.** Refuse everything and recall is 1.00.
4. **Judging with the generator.** Self-preference is real. Different tier.
5. **Leaving `build_retriever()` as the placeholder.**

## Common errors

| Symptom | Cause |
|---|---|
| `NotImplementedError` | One of the five TODOs |
| Citation validity < 1.00 | Validator not on the return path |
| Faithfulness much lower than correctness | Almost always truncated judge verdicts |
| `judge_agreement` raises | Your two lists differ in length — one label is missing |
| Cost above budget on `--full` | 45 questions × (generate + 2 judges). Check your tier |
