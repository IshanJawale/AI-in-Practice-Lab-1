# Lab 7 — start here

An **add-on** to the folder you already have — and, because this is the last
lab, a **refresh of every document in the module**.

> **It cannot overwrite your work.** No code file from Labs 1–6 is in this zip,
> no `report.md`, no `.env`, nothing in `reports/`, and not your `.aip_cache/`.
> The only files it replaces are ones you were never meant to edit — the
> handouts, the theory notes, the decks, and `aip/`.

## 1 · Install it

```bash
unzip -o AI-in-Practice-Lab7.zip -d aip-lab1
```

**Use the `-o`.** About 55 files already exist in your folder; without it,
`unzip` asks about each one, and answering "no" keeps the stale version
silently. It is safe — nothing in this zip is a file you have written.

## 2 · Environment

Nothing new to install — FastAPI, uvicorn, Streamlit and `sse-starlette` all
came with `make setup-full`. Confirm:

```bash
make check
python -c "import fastapi, uvicorn, streamlit, sse_starlette; print('service stack ok')"
```

> **Done when:** both print cleanly.

## 3 · ⚠️ This lab is 36% of Module 1

**20% for the system, 16% for the evaluation report.** More than twice most
labs. Two consequences:

- **Come with your best pipeline working.** Lab 7 is integration, not
  invention. If Labs 3–5 are unfinished, get them running first — you will not
  have time to build them here.
- **Part E is 16% and gets 20 minutes.** Do not let it be what you run out of
  time for. Skim the seven required sections now so you know what you are
  collecting numbers for all session.

## 4 · What to have ready

- [ ] Your **Labs 3–5 pipeline**, running
- [ ] Your **Lab 6 guards** — both go in. A service with no guards is not
      shippable and it is explicitly graded
- [ ] `reports/lab4.json` and your Lab 5 before/after numbers — Part E quotes them

## 5 · Read, in this order

| # | File | When | What it is |
|---|---|---|---|
| 1 | `labs/lab7/OVERVIEW.md` | before | **start here.** Why this lab exists |
| 2 | `labs/lab7/README.md` | before | the brief: targets, deliverables, rubric |
| 3 | `labs/lab7/CODE_GUIDE.md` | before | five files, the `aip/` API, every TODO itemised |
| 4 | `labs/lab7/RUNSHEET.md` | **in the lab** | the step-by-step |
| 5 | `labs/lab7/CONCEPTS.md` | **in the lab** | concept → code → theory |

Also included: `quizzes/lab7_quiz.html`, for the end of the session.

## 5a · The rest of the module, refreshed

Lab 7 integrates everything, so the zip also brings the **current** version of
every document you will want open while you do it:

| What | Where |
|---|---|
| Handouts for Labs 1–6 — `README`, `OVERVIEW`, `CONCEPTS`, `RUNSHEET`, and the code guides | `labs/lab1/` … `labs/lab6/` |
| All four theory notes, including T1 §4.1 (caching, SLOs, alerts) and T3 §5.3 (regression gates), which this lab leans on | `theory/` |
| All four lecture decks | `decks/` |
| The `aip` reference — every module, and which lab uses it | `aip/README.md`, `docs/aip-reference.html` |

Several of these were corrected after you first received them. Where your copy
and this one differ, **this one is right.**

## 6 · Demo day

The last **25 minutes are live, on the projector** — five minutes per pair.
Have a question it answers well and a question it correctly refuses **picked in
advance**, and your `/metrics` page already open. Item 5 — your worst remaining
failure — **is graded.**

---

## Troubleshooting

### Every request takes several seconds, even cached
You are building the pipeline **per request**. Build it once at startup and
cache it — this is TODO A2 and it is the most common cause.

### A provider outage returns 500 with a stack trace
TODO A3. An outage is a **503 with `Retry-After`**; budget exhaustion is a
**429**; a malformed request is a **422**. Test all three with `curl`.

### CI fails with a missing API key
The workflow runs `AIP_OFFLINE=1` against your **committed cache**. If you have
not committed `.aip_cache/`, there is nothing to replay.

### The regression gate passes after I deliberately broke something
Your thresholds are too loose. That is exactly what D3 is for — a gate you have
not seen fail is a gate you do not have.

### The semantic cache returns a confidently wrong answer
**That is the finding**, not a bug. Find the cosine threshold where it starts
happening and report it. It is lower than you expect.

### `/metrics` is empty
No traces have been written yet, or you are reading the wrong directory. Check
`aip.tracing.read_traces()` and that `.aip_traces/` exists.

**Stuck for more than ten minutes? Ask.**
