# Lab 3 — start here

This is an **add-on** to the folder you already have. It adds Lab 3 and
refreshes anything that has changed since the last drop.

> **It cannot overwrite your work.** The files you edit — `labs/lab1/extract.py`,
> `labs/lab1/pydantic_primer.py`, `labs/lab1/v0_naive.py`,
> `labs/lab2/variants.py` — are **not in this zip at all**. Neither is `.env`
> or anything in `reports/`.

## 1 · Install it

From a terminal, in the folder containing your `aip-lab1` directory:

```bash
unzip AI-in-Practice-Lab3.zip -d aip-lab1
```

*(Double-clicking in Finder or Explorer unpacks it into its own folder instead.
If that happens, drag the folders into `aip-lab1` and merge when prompted —
nothing you wrote gets replaced.)*

## 2 · ⚠️ You DO need to install something this time

**This is the one thing that will ruin your session if you skip it.**

Labs 1 and 2 ran on a 290 MB install. **Lab 3 is the first lab that needs the
full one** — it uses `chromadb`, `rank_bm25` and `sentence_transformers`, and
that last one pulls in PyTorch.

```bash
make setup-full
```

**~1.8 GB. Several minutes on a good connection, much longer on a bad one.
Do it the night before.** If you arrive without it you will spend the first
forty minutes of a three-hour lab watching a progress bar.

Then confirm:

```bash
make check
```

> **Done when:** the last line reads `Environment is ready.` — with **no**
> `warn` lines left about `chromadb`, `rank_bm25` or `sentence_transformers`.
> Those warnings were fine for Labs 1 and 2. They are not fine now.

## 3 · Warm the index — 3 min

```bash
python labs/lab3/search.py --baseline
```

The first run embeds the corpus and takes 1–3 minutes. Every run after that is
instant, because the cache is content-addressed. **Do this before the lab so
you are not waiting on it in the room.**

> **Done when:** you see a baseline table with nDCG@10, recall@5, hit_rate@1
> and MRR. **Write those four numbers down.**

## 4 · Read, in this order

| # | File | When | What it is |
|---|---|---|---|
| 1 | `labs/lab3/OVERVIEW.md` | before | **start here.** Why this lab exists and how to approach it |
| 2 | `labs/lab3/README.md` | before | the brief: search space, targets, deliverables, rubric |
| 3 | `theory/T4-retrieval-engineering.md` | before | §2 chunking, §4 retrieval, §5 failure modes |
| 4 | `labs/lab3/RUNSHEET.md` | **in the lab** | the step-by-step. Follow it top to bottom |
| 5 | `labs/lab3/CONCEPTS.md` | **in the lab** | concept → code → theory, for when you are stuck |

Also included: `quizzes/lab3_quiz.html` — open it in a browser after the lab.
Not graded, no score shown; we go through the answers together.

## 5 · This lab is in pairs

Decide who drives first and **swap at each part**. The person not typing reads
the numbers aloud and challenges them. Two people watching one screen and
agreeing is not pair work.

## 6 · Before the lab — checklist

- [ ] `make setup-full` done, `make check` clean with no warns
- [ ] `python labs/lab3/search.py --baseline` runs, four numbers written down
- [ ] `OVERVIEW.md` read
- [ ] T4 §2, §4 and §5 skimmed

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'chromadb'` (or `sentence_transformers`)

You are still on the Labs 1–2 install. Run `make setup-full`. See §2.

### `make setup-full` is very slow or fails on `sentence-transformers`

It is downloading PyTorch, which is large. Give it time and a decent
connection. This is the single reason to do it the night before.

### The first `--baseline` run seems stuck

It is embedding 30 documents. One to three minutes, once. Subsequent runs read
the cache and are instant.

### All four chunking strategies give the same score

Your chunker is not actually being applied — you are almost certainly
rebuilding the retriever while reading a cached index. Check that the chunks
actually changed by printing the chunk count.

### The per-question-kind table shows no difference between retrievers

You are looking at `hit_rate@5`, which is **saturated** on this corpus — every
retriever scores 0.93–0.98. Use **MRR** or nDCG. This is deliberate, and it is
one of the lessons of the lab.

### `recall` is `nan` for some questions

Q36, Q38 and Q39 have **no** relevant document, so recall is undefined. Exclude
those three; you are working with **n = 42**, and your report should say so.

### The LLM reranker takes forever

It makes 30 **sequential** model calls. That is not a bug in the lab — it is the
measurement. Parallelising them is the obvious fix and a legitimate thing to
report.

**Stuck for more than ten minutes? Post on the course channel** with the exact
command and the full error. Do not lose the lab to setup.
