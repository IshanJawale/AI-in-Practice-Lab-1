# Lab 5 — start here

An **add-on** to the folder you already have. It adds Lab 5 and refreshes
anything changed since the last drop.

> **It cannot overwrite your work.** Every file you have edited —
> `labs/lab1/extract.py`, `labs/lab2/variants.py`, `labs/lab3/search.py`,
> `labs/lab4/rag.py`, `labs/lab4/evaluate.py` and any later lab file you have
> started — is **not in this zip**. Neither is `.env` or anything in `reports/`.

## 1 · Install it

```bash
unzip AI-in-Practice-Lab5.zip -d aip-lab1
```

*(Double-clicking unpacks it into its own folder instead. If that happens, drag
the folders in and merge when prompted — nothing you wrote is replaced.)*

## 2 · Environment

Nothing new to install. If `make setup-full` worked for Lab 3 you are ready:

```bash
make check
```

> **Done when:** `Environment is ready.` with no warn lines.

## 3 · ⚠️ You need `reports/lab4.json`

**This is a hard prerequisite.** Lab 5 reads your Lab 4 output — it is the list
of failures you are going to diagnose. Confirm it exists:

```bash
ls -l reports/lab4.json
```

If it is missing, run Lab 4's full evaluation before you come:

```bash
python labs/lab4/evaluate.py --full --save reports/lab4.json
```

**Bring your ten tagged failures from Lab 4 E3 as well.** They are your starting
backlog, and the lab opens with them.

## 4 · Read, in this order

| # | File | When | What it is |
|---|---|---|---|
| 1 | `labs/lab5/OVERVIEW.md` | before | **start here.** Why this lab exists |
| 2 | `labs/lab5/README.md` | before | the brief: targets, deliverables, rubric |
| 3 | `labs/lab5/CODE_GUIDE.md` | before | the files, the `aip/` API, every TODO itemised |
| 4 | `labs/lab5/RUNSHEET.md` | **in the lab** | the step-by-step |
| 5 | `labs/lab5/CONCEPTS.md` | **in the lab** | concept → code → theory |

Also included: `quizzes/lab5_quiz.html`, for after the lab. Not graded, no
score shown; we go through the answers together.

## 5 · Pairs

Swap driver at each part. The one not typing reads the numbers aloud and
challenges them.

## 6 · Before the lab — checklist

- [ ] `reports/lab4.json` exists
- [ ] Your ten tagged Lab 4 failures in hand
- [ ] `OVERVIEW.md` and `CODE_GUIDE.md` read
- [ ] **T4 §5 re-read** — the seven failure modes and the diagnostic tree

---

## One thing to know before you start

**You are graded on the process, not the score.** When the reference solution
ran this lab it diagnosed correctly, chose a well-motivated fix, predicted 4–6
recoveries — and measured **−0.050 correctness.** The fix made things worse.

That is a full-marks Lab 5. Diagnose before you fix, predict before you measure,
and report what happened rather than what you hoped.

---

## Troubleshooting

### `FileNotFoundError: reports/lab4.json`
Lab 4's `--full --save` was never run. See §3.

### My tally is spread evenly across all seven modes
You have almost certainly mis-classified. Re-read the diagnostic tree, and
re-check the mode-6 test — **gold context *fixing* the answer means RETRIEVAL
was at fault**, not generation. People invert this constantly.

### Everything landed in mode 6
Normal, if you started from a strong Lab 3 retriever. The reference found 13 of
14 there. Not a bug.

### Everything is `needs_human_check`
The branches above that point in `classify()` are still TODO.

### Cost went up after my fix
HyDE and multi-query each add a model call per query. Expected — and the ≤ 2×
budget rule is why you measure it.

**Stuck more than ten minutes? Ask.**
