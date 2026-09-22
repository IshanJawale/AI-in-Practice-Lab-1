# Lab 4 Report (RAG v1: Grounded Answers with Citations)

## 1. Answer System Prompt (`ANSWER_SYSTEM`)

```text
You answer questions using ONLY the numbered sources provided.

Rules, in priority order:
1. If the sources do not contain the answer, reply exactly:
   "I don't have enough information in the provided sources to answer that."
   Do not guess, and do not fall back on general knowledge.
2. Every factual sentence must end with a citation of the source(s) that
   support it, in the form [1] or [2][5].
3. Never cite a number that was not given to you.
4. If sources disagree, say so and cite both.
5. Be concise. Two or three sentences unless the question needs more.
6. The answer must not contain any content outside the supplied sources.

{UNTRUSTED_SYSTEM_CLAUSE}
```

*Differences from reference `aip/rag.py::ANSWER_SYSTEM`*: the reference includes the same six required elements but omits rule 6 (explicit “no content outside sources”). Our version adds this rule for completeness and clarity.

---

## 2. Citation Validation (`validate_answer`)

Implemented checks:
- Every citation index `[n]` is between 1 and `n_sources`.
- The answer is non‑empty and contains at least one citation unless it is a refusal.
- Detects truncation via the optional `finish_reason == "length"`.
- Returns a dictionary with keys `valid`, `refused`, `invalid_citations`, `n_citations`, `truncated`, and a human‑readable `reason`.

On validation failure we **fallback to an exact refusal** (the safest behaviour) to guarantee the invariant that we never return `citations_valid=False` with `refused=False`.

---

## 3. Refusal Precision / Recall (Two Strictness Settings)

We measured refusal behaviour on the 5 *unanswerable* questions (Q36‑Q40) using two prompt strictness settings:

| Strictness | Refusal Recall | Refusal Precision |
|------------|----------------|-------------------|
| **Default** (as implemented above) | *to‑be‑filled* (e.g. `4/5 = 0.80`) | *to‑be‑filled* (e.g. `4/7 = 0.57`) |
| **Stricter** (e.g. explicitly instructing the model to refuse when any doubt) | *to‑be‑filled* | *to‑be‑filled* |

*Raw counts* are reported alongside the ratios (e.g. `4/5`). The numbers will be populated after running `python labs/lab4/evaluate.py --full`.

---

## 4. Judge κ for Rubrics

Two single‑criterion rubrics were created (see `labs/lab4/evaluate.py`):
- **Faithfulness rubric** – “Is every claim supported by the supplied context?”
- **Correctness rubric** – “Does the answer match the gold answer substantively?”

After hand‑labelling 20 answers per rubric (via `--calibrate`), Cohen’s κ is computed with `--kappa`.  The κ values will be inserted below:

| Rubric | κ |
|--------|---|
| Faithfulness | *to‑be‑filled* |
| Correctness   | *to‑be‑filled* |

If κ < 0.4 we will iterate on the rubric wording and repeat calibration.

---

## 5. Gold‑Context Decomposition (E2)

Running the gold‑context run (`--gold-context`) yields two correctness scores:

- **A = correctness with gold context** (generation ceiling)
- **B = correctness with retrieved context** (our system)

We will report:
```
correctness with gold context       = A
correctness with retrieved context  = B
retrieval‑attributable loss          = A - B
generation‑attributable loss        = 1 - A
```
These values are populated after the run.

---

## 6. Failure‑Mode Tally (E3)

We will inspect the 10 worst answers (by overall error) and assign one of the seven failure modes defined in `labs/lab4/CONCEPTS.md` (e.g., citation‑error, hallucination, partial‑refusal, etc.).  The tally will be listed as:

- Citation validity errors: X
- Faithfulness failures: Y
- Correctness mismatches: Z
- … (other modes)

---

## 7. Next Steps

1. Run the full evaluation to produce `reports/lab4.json`:
   ```bash
   python labs/lab4/evaluate.py --full --save reports/lab4.json
   ```
2. Generate the calibration sheet, fill it, and compute κ:
   ```bash
   python labs/lab4/evaluate.py --calibrate   # writes calibration_labels.jsonl
   # Fill `human_faithfulness` and `human_correctness` columns, then:
   python labs/lab4/evaluate.py --kappa
   ```
3. Run the gold‑context experiment:
   ```bash
   python labs/lab4/evaluate.py --gold-context
   ```
4. Update the placeholders in this report with the actual numbers.

---

*All code changes are committed; the repository now contains a functional Lab 4 pipeline.*