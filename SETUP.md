# Setup

Budget 30 minutes. Do it **before** the first lab, not at the start of it.

> **First time?** Start with [`PRE_MODULE_SETUP.md`](PRE_MODULE_SETUP.md) — it is
> the same thing as a short checklist, with an example of what a successful
> `make check` looks like. This file is the fuller reference and the
> troubleshooting table.

---

## 1. Python and dependencies

Python 3.11 or later. Verified on 3.13 and 3.14.

Why 3.11 and not 3.10: the code itself only needs 3.10 (Pydantic evaluates
`str | None` annotations at runtime, which is a 3.10 feature), but on 3.10 pip
resolves pandas, matplotlib and scikit-learn to older releases, and current
numpy and scipy require 3.12. 3.11 is the lowest version where you get a
sensible, supported dependency set.

**Upper bound: below 3.15**, which is litellm's own ceiling.

```bash
git clone https://github.com/subratpanda/ai-in-practice-1-module-1-students.git aip-module1
cd aip-module1
make setup
```

`make setup` creates `.venv/` and installs into it. **Activation is optional** —
`make` targets locate `.venv` themselves. `make help` prints which interpreter
it has chosen, which is the first thing to check when something looks wrong.

`sentence-transformers` pulls in PyTorch and is the slow part (~2 GB, a few
minutes). It is required: it is what makes the zero-cost embedding path work.

---

## 2. Choose a provider

Copy the template and fill in **one** provider:

```bash
cp .env.example .env
```

| Profile | Cost | Get a key | Notes |
|---|---|---|---|
| **`gemini`** | free tier | aistudio.google.com/apikey | **Recommended.** Generous free quota, good structured output. All measured lab targets are on this profile |
| **`nvidia`** | free developer tier | build.nvidia.com | **Verified end to end.** The recommended fallback if Gemini gives you trouble. Nemotron models; see the note below |
| **`groq`** | free tier | console.groq.com/keys | Very fast, open-weight models, tighter rate limits |
| `anthropic` | paid | console.anthropic.com | Best structured output and tool use |
| `openai` | paid | platform.openai.com | |
| `ollama` | free, local | ollama.com | No key, no network, works on a plane. Slower, and weaker on structured output |

Set `AIP_PROFILE` to your choice and paste the matching key.

### If you use the `nvidia` profile

Set `AIP_PROFILE=nvidia` and put your key in `.env` as `NVIDIA_API_KEY`
(the name NVIDIA itself uses — the toolkit bridges it to what LiteLLM expects).

Two things to know, both measured rather than guessed:

**Raise `max_tokens`.** The nemotron models *reason in their visible output* —
a response opens with "We need to output JSON with fields…" and only then emits
the object. At `max_tokens=700` they are truncated before producing any JSON.
`aip.llm.structured` detects this and retries with double the budget, so nothing
breaks, but you pay an extra round-trip on every call. Passing `max_tokens=2500`
up front removes it entirely: 60 tickets went from 119 calls to 60.

**Expect lower accuracy on Lab 1 than the published targets.** Measured on the
same 60-item dev split: field accuracy **0.881** against Gemini's 0.929, record
accuracy **0.400** against 0.650, and p95 latency 15.8 s against 2.6 s. Schema
validity is 1.000 on both. Most of the gap is the `urgency` field (0.567 vs
0.750). The lab targets are set against Gemini; if you are on NVIDIA, say so in
your report and quote your own baseline rather than the published one.

### The fully local path

```bash
ollama serve                 # in a second terminal
ollama pull llama3.1:8b
ollama pull llama3.2:3b
```

Then `AIP_PROFILE=ollama`. Everything in Module 1 runs, but expect lower
accuracy on Labs 1–2 and slower iteration. Budget 8 GB of RAM.

---

## 3. Verify

```bash
make check
```

Expected: every line `ok`, one live model call, and a cost report. If anything
fails, the message names the fix.

---

## 4. Cost control

This module is designed to cost **between $0 and $6 per student in total**, and
$0 if you use a free tier or Ollama.

Four mechanisms protect you, and all four are on by default:

1. **`AIP_BUDGET_USD=2.0`** — a hard process ceiling. Any call that would push
   spend past it raises `BudgetExceeded` and stops the run. It is not a warning.
2. **The response cache** — identical requests are served from SQLite, free and
   instant. Re-running an eval after a code change costs nothing for the calls
   that did not change.
3. **Tier defaults** — labs use the `SMALL` tier unless a task needs more.
4. **Per-lab budgets** — each lab script wraps its work in a `Budget` with a
   sensible limit.

Check spending any time:

```bash
make cost
```

### Offline mode

```bash
AIP_OFFLINE=1 python labs/lab1/run_eval.py --split dev --variant c
```

Serves only from cache; a cache miss raises `CacheMiss` rather than spending.
Use it to demo without wifi, to grade, and to guarantee a run is free. The CI
regression gate in Lab 7 uses it.

---

## 5. Rate limits

**Measure yours before the lab, do not guess:**

```bash
python scripts/check_rate_limit.py
```

Google no longer publishes fixed free-tier RPM figures — they are per key and
live in the AI Studio dashboard. Linking a billing account silently moves a key
to Tier 1 with far higher limits, so **one person's key tells you nothing about
another's.**

Lab 1 needs about 500 calls over three hours. The probe tells you whether yours
can take that and which `--workers` to use.

If you see 429s:

- Drop `--workers` to 2 or 1.
- The client already retries with exponential backoff **and jitter** — the
  jitter matters because 27 students hitting the same free tier in the same
  three-hour window is a thundering herd.
- Ask a neighbour on a different provider to run a sweep you both need, and
  share the cache file. This is legitimate and encouraged.

---

## 6. Repository layout

```
aip/                    the shared toolkit. Read it. You will modify it
  config.py             model tiers, prices, settings
  llm.py                chat() and structured() with retry/cache/repair
  embed.py              embeddings with a local fallback
  chunking.py           four chunking strategies
  retrieval.py          dense, BM25, hybrid, rerankers, Chroma
  rag.py                reference RAG pipeline (Lab 4 comparison)
  evals.py              the harness: metrics, runner, judge, compare()
  guards.py             injection defences, PII, tool guard, citations
  cache.py, cost.py, tracing.py

data/
  corpus/               30 documents: 16 Aurora Health policy docs plus
                        14 lexically-competing distractors (Labs 3-7)
  eval/                 golden sets
  tickets/              240 support tickets (Labs 1-2)
  attacks/              21-case red-team suite (Lab 6)

labs/lab1 .. lab7       handout + starter code per lab
theory/                 T1-T4 lecture notes
rubrics/                grading rubrics
scripts/                setup check, data generation
tests/                  unit tests
```

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `make: python: No such file or directory` | An old Makefile that assumed `python` exists. macOS and most Linux distributions only ship `python3` | Pull the latest — the Makefile now detects the interpreter. `make help` shows which one it picked |
| `404 ... is no longer available` | The model ID in `aip/config.py` has been retired. This *will* happen | `python scripts/list_models.py`, then update the profile. Every ID in the first version of this repo was dead within months |
| A model is listed but 404s or 429s | Listed ≠ callable on your key. Free tiers exclude the pro models | Pick one that actually responds; the script warns about this |
| Output tokens far higher than expected | Reasoning models spend invisible "thinking" tokens you pay for. `gemini-3.7-flash` uses ~220 per call and it cannot be disabled | Use the `SMALL` tier for high-volume loops; it spends none |
| A judge or extractor returns garbage on long outputs | Truncation. A reasoning model burns its budget thinking, then gets cut off mid-JSON | Raise `max_tokens`, and always check `finish_reason` |
| `BudgetExceeded` immediately | A previous run in the same process spent it | Restart the process, or raise `AIP_BUDGET_USD` deliberately |
| `CacheMiss` | `AIP_OFFLINE=1` and the request is new | Unset `AIP_OFFLINE`, or run once online to populate |
| First embed call takes minutes | Downloading the local model (~130 MB) | Once only. Later calls are instant |
| `429` on every call | Free-tier rate limit | `--workers 1`, wait a minute |
| Ollama: `connection refused` | Server not running | `ollama serve` |
| Chroma: dimension mismatch | You changed embedding model with an existing index | `rm -rf .chroma` and rebuild |
| Structured output always fails on Ollama | Small local models are weak at JSON | Use `max_repairs=3`, a smaller schema, or switch profile for that lab |
| Eval numbers change between runs | `AIP_TEMPERATURE > 0`, or cache off | Set temperature 0 and `AIP_CACHE=1` |
