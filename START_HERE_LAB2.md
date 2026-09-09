# Lab 2 — start here

This is an **add-on** to the Lab 1 folder you already have. It contains no file
that exists in the Lab 1 zip, so it **cannot overwrite your work** — in
particular it will not touch your `labs/lab1/extract.py`.

## 1 · Install it

From a terminal, in the folder that contains your `aip-lab1` directory:

```bash
unzip AI-in-Practice-Lab2.zip -d aip-lab1
```

*(Double-clicking the zip in Finder or Explorer will unpack it into its own
folder instead. If you do that, drag `labs/lab2`, `theory` and `decks` into
your `aip-lab1` folder and merge when prompted — nothing will be replaced.)*

Check it landed:

```bash
cd aip-lab1
python labs/lab2/stats.py
```

You should see two overlapping confidence intervals and a paired test. **Read
that output — it is the whole argument of this lab in twenty lines.**

## 2 · You need nothing new installed

No new dependencies. If `make check` worked for Lab 1, you are ready. The three
`warn` lines about `chromadb`, `rank_bm25` and `sentence_transformers` are still
expected and still fine — those are for Lab 3.

## 3 · Lab 1 must be finished

**This is the one hard prerequisite.** `labs/lab2/variants.py` imports your own
`labs/lab1/extract.py`:

```python
from labs.lab1.extract import (
    SYSTEM_PROMPT, TicketRecord, apply_business_rules, extract_deterministic,
)
```

A broken or unfinished Lab 1 is a broken Lab 2. Confirm it still runs:

```bash
python labs/lab1/run_eval.py --split dev --variant c --n 5
```

If that errors, fix Lab 1 first. Come and ask if you are stuck — do not arrive
hoping to sort it out in the room.

## 4 · Read, in this order

| # | File | Time |
|---|---|---|
| 1 | `labs/lab2/OVERVIEW.md` | 15 min — **start here.** Plain language: what you are doing and why |
| 2 | `labs/lab2/README.md` | 20 min — the brief: parts, targets, rubric |
| 3 | `theory/T3-evaluation-driven-development.md` | the theory this lab is the practical half of |
| 4 | `aip/evals.py` | **all of it.** It is the instrument; know what it measures |

`theory/T4-*` and `decks/T4-*` are also included — that is the retrieval half of
the same theory session. You need it from Lab 3, not for this lab.

## 5 · Before the lab

- [ ] `python labs/lab2/stats.py` runs and you understand its output
- [ ] Lab 1 still passes on dev
- [ ] `OVERVIEW.md` read
- [ ] You have skimmed `aip/evals.py`

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'labs.lab2'`

Run commands from the **repo root** (`aip-lab1/`), not from inside `labs/`.

### `NotImplementedError` from `grid.py`

Expected before you start — `variants.py` is a skeleton with TODOs. The harness
now tells you which variant died and why instead of crashing.

### `ImportError` from `labs.lab1.extract`

Lab 1 is unfinished or broken. See §3.

### The cascade reports `escalated 0.00`

Read the warning in `README.md` Part C. This is a **deliberate trap** and it is
not a bug in the harness. Two identical calls at temperature 0 are the same
request, so the cache serves the second from the first, the answers match
byte-for-byte, and disagreement can never be detected.

### `cost` says `UNPRICED` instead of dollars

You are on `AIP_PROFILE=nvidia`. NVIDIA publishes no per-token prices, so the
harness reports the **tokens** it actually measured rather than a confident and
wrong `$0.00`. Compare variants on tokens — cost is proportional to them, so
the ranking is unchanged.

**On Gemini if you can.** Everything in this lab is calibrated on it, and NVIDIA
is 7–10× slower here. On NVIDIA, use `--n 20` rather than the full 60.

### The grid is slow

Normal. It is 7 configurations × 60 tickets. Caching means a re-run is nearly
free, so the *second* pass is fast. Start it, then go read `aip/evals.py`.
