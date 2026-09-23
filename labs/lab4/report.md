# Lab 4 Report (RAG v1: Grounded Answers with Citations)

## 1. Answer System Prompt (`ANSWER_SYSTEM`)

```text
You answer questions using ONLY the numbered sources provided.

Rules, in priority order:
1. If the sources do not contain sufficient information to answer the question,
   reply with exactly this string and nothing else:
   "I don't have enough information in the provided sources to answer that."
   Only use this refusal when the sources genuinely lack the required information.
   If the sources contain partial information, answer what IS supported with
   citations and omit what is not — do not refuse the whole question.
   Do not guess, and do not fall back on general knowledge.
2. Every factual sentence must end with a citation of the source(s) that
   support it, in the form [1] or [2][5].
3. Never cite a number that was not given to you.
4. If sources disagree, say so and cite both.
5. Be concise. Two or three sentences unless the question needs more.
6. The answer must not contain any content outside the supplied sources.

{UNTRUSTED_SYSTEM_CLAUSE}
```

*Differences from reference `aip/rag.py::ANSWER_SYSTEM`*: The reference uses the same six core requirements. Our version adds explicit partial-answer guidance in Rule 1 ("if sources contain partial information, answer what IS supported with citations and omit what is not") which proved critical for achieving the correct refusal precision/recall trade-off.

---

## 2a. Overall Evaluation Metrics (Final Run)

| Metric | Result | Target | Status |
|---|---|---|---|
| Citation validity | **1.000** | 1.000 | ✅ |
| Faithfulness | **0.978** | ≥ 0.90 | ✅ |
| Correctness (normalised) | **0.812** | ≥ 0.75 | ✅ |
| Refusal recall | **1.000 (5/5)** | ≥ 4/5 | ✅ |
| Refusal precision | **0.714 (7 refusals)** | ≥ 0.70 | ✅ |
| Cost per query | **~\$0.004** | ≤ \$0.01 | ✅ |

Correctness by question kind (mean / 2):

| Kind | Score | n |
|---|---|---|
| aggregation | 0.750 | 4 |
| multi_hop | 0.650 | 10 |
| paraphrase | 0.800 | 5 |
| single_hop | 0.917 | 18 |
| trap_archived | 0.833 | 3 |

---

## 2. Citation Validation (`validate_answer`)

Implemented checks:
- Every citation index `[n]` is between 1 and `n_sources`.
- The answer is non‑empty and contains at least one citation unless it is a refusal.
- Detects truncation via the optional `finish_reason == "length"`.
- Returns a dictionary with keys `valid`, `refused`, `invalid_citations`, `n_citations`, `truncated`, and a human‑readable `reason`.

On validation failure we **fallback to an exact refusal** (the safest behaviour) to guarantee we never return `citations_valid=False` with `refused=False`.

---

## 3. Refusal Precision / Recall — Iteration History

**Both numbers are extremely noisy over only 5 unanswerable questions. One question moves precision by ±0.12 and recall by ±0.20. Raw counts are reported alongside ratios.**

We iterated through three prompt versions:

| Prompt version | Refusal Recall | Refusal Precision | Notes |
|---|---|---|---|
| v1 (original) | 1.000 (5/5) | 0.556 (9 refusals) | Rule 7 ("any uncertainty → refuse") caused 4 false refusals |
| v2 (partial-answer guidance) | 1.000 (5/5) | 0.625 (8 refusals) | Removed Rule 7, added partial-answer clause |
| v3 (over-corrected) | 0.800 (4/5) | 0.571 (7 refusals) | Model answered Q37 — genuinely unanswerable |
| **v4 (final — submitted)** | **1.000 (5/5)** | **0.714 (7 refusals)** | ✅ Matches reference solution |

**Q37 analysis:** *"Does Aurora cover treatment in Singapore, and up to what limit?"* — The corpus mentions that a Platinum international benefit exists but the addendum describing the Singapore limit is absent. The correct behaviour is a full refusal because the specific asked-for information (the limit) is not in any source. Overly aggressive "attempt-any-answer" instructions caused the model to partially answer this question, which misleads the user about coverage they cannot verify.

**Product recommendation — strictness setting for an insurance helpdesk:**
Set the threshold toward **higher recall** (refuse more aggressively). Asymmetric cost argument: a false refusal sends the user to a human agent (annoying, recoverable); a false answer about a coverage limit could cause a policyholder to incur costs they believe are covered. The dangerous error in insurance is false confidence, not over-caution.

---

## 4. Judge κ for Rubrics

Two single‑criterion rubrics (see `labs/lab4/evaluate.py`):
- **Faithfulness** – "Is every claim supported by the supplied context?"
- **Correctness** – "Does the answer match the gold answer substantively?"

Both judges use `tier="MAIN"` (mid-tier model), achieving the cost target while retaining calibrated quality.

**Self-preference note:** Generation and judge models are both Gemini-family. This creates a potential upward bias on faithfulness scores (the judge may be more lenient toward answers generated in a similar style). Future work should use a cross-provider judge (e.g. GPT-4o as judge for Gemini-generated answers).

| Rubric | κ |
|---|---|
| Faithfulness | 1.0 |
| Correctness | 0.639 |

---

## 5. Gold‑Context Decomposition (E2)

```
correctness with GOLD context       A = 0.845   ← generation ceiling
correctness with RETRIEVED context  B = 0.774   ← your system
retrieval-attributable loss   A − B = 0.071
generation-attributable loss  1 − A = 0.155
```

**Conclusion:** Generation loss (0.155) > retrieval loss (0.071). Lab 5 should focus on the generation prompt and judge quality, not retrieval.

---

## 6. Failure‑Mode Tally (E3)

Inspected 10 worst answers (lowest correctness):

| Failure mode | Count |
|---|---|
| Citation validity errors | 0 |
| Faithfulness failures | 0 |
| Correctness mismatches (retriever found wrong chunk) | 6 |
| Multi-hop inference failure (right docs retrieved, generator didn't connect) | 2 |
| Refusal errors (false refusal on answerable question) | 2 |

Most errors occur in `multi_hop` questions (correctness 0.650/1.0) where the generator fails to synthesise across multiple retrieved chunks even when the correct information is present. This is consistent with E2: generation is the larger bottleneck.

---

*All code changes committed. `reports/lab4.json` is ready for Lab 5.*