# Lab 4 — start here

An **add-on** to the folder you already have. It adds Lab 4 and refreshes
anything changed since the last drop.

> **It cannot overwrite your work.** Every file you have edited —
> `labs/lab1/extract.py`, `labs/lab2/variants.py`, `labs/lab3/search.py`,
> and any later lab file you have started — is **not in this zip**. Neither is
> `.env` or anything in `reports/`.

## 1 · Install it

```bash
unzip AI-in-Practice-Lab4.zip -d aip-lab1
```

*(Double-clicking unpacks it into its own folder instead. If that happens, drag
the folders in and merge when prompted — nothing you wrote is replaced.)*

## 2 · Environment

Nothing new to install. If `make setup-full` worked for Lab 3, you are ready:

```bash
make check
```

> **Done when:** `Environment is ready.` with no warn lines.

## 3 · ⚠️ You need your Lab 3 result

Lab 4 generates answers from passages **your Lab 3 retriever** finds. The first
thing you will do is put your winning Lab 3 configuration into
`build_retriever()` in `labs/lab4/evaluate.py`.

**Come knowing your Lab 3 answer:** chunking strategy, chunk size, retriever,
and `final_k`. If Lab 3 is unfinished, the reference configuration —
markdown-aware chunking at 400 characters with exact dense retrieval — is a
legitimate starting point. Say in your report that you used it.

Check it still runs:

```bash
python labs/lab3/search.py --baseline
```

## 4 · Read, in this order

| # | File | When | What it is |
|---|---|---|---|
| 1 | `labs/lab4/OVERVIEW.md` | before | **start here.** Why this lab exists |
| 2 | `labs/lab4/README.md` | before | the brief: targets, deliverables, rubric |
| 3 | `labs/lab4/CODE_GUIDE.md` | before | the files, the `aip/` API, every TODO itemised |
| 4 | `labs/lab4/RUNSHEET.md` | **in the lab** | the step-by-step |
| 5 | `labs/lab4/CONCEPTS.md` | **in the lab** | concept → code → theory |

Also included: `quizzes/lab4_quiz.html`, for after the lab. Not graded, no
score shown; we go through the answers together.

## 5 · Pairs

Decide who drives first and **swap at each part**. The one not typing reads the
numbers aloud and challenges them.

## 6 · Before the lab — checklist

- [ ] `make check` clean
- [ ] Your Lab 3 configuration written down
- [ ] `OVERVIEW.md` and `CODE_GUIDE.md` read
- [ ] T4 §6 (generation, citation, refusal) and **T3 §4 (LLM-as-judge)** skimmed

---

## Troubleshooting

### Citation validity is below 1.00
It is a **code** guarantee, not a model behaviour. Your validator is not on the
return path — the answer is being returned before, or regardless of, the check.

### Faithfulness looks much worse than correctness
Almost always **truncated judge verdicts**, not bad answers. A reasoning judge
spends most of its token budget on invisible thinking; if the JSON is cut off it
fails to parse and gets scored 0. Check `finish_reason` and `parse_error`
before you believe the number.

### `judge_agreement` raises a length error
Your judge list and your human list are different lengths — you skipped a label.

### Refusal numbers swing wildly between runs
There are only **five** unanswerable questions. One case moves precision by 0.12
and recall by 0.20. That is the metric, not a bug. Report raw counts.

### `--full` costs more than expected
45 questions × (one generation + two judge calls). Check which tier your judge
is on, and that the cache is working.

**Stuck more than ten minutes? Ask.**
