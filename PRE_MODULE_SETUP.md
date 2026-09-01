# Before the module starts — do this

**Budget 45 minutes. Do it this week, not on the morning of the first lab.**

You need three things working before Session 2: Python, an API key, and the
repository. None is hard. All three go wrong occasionally, which is why there
is a setup session — come to it with as much of this done as you can, and we
will fix whatever is left together.

There is nothing to submit. You are done when one command says so.

---

## What this costs you

**Nothing.** The module runs on Google's free Gemini tier. You will not be asked
for a card, and the code has a hard spending ceiling built in that stops the run
rather than quietly billing you.

If you would rather not create an API key at all, there is a fully offline path
using a local model — see step 2, option C.

---

## Step 1 — Python 3.11 or later

```bash
python3 --version
```

**Supported: 3.11 up to (but not including) 3.15.** Verified on 3.13 and 3.14.
If yours is in that range, skip ahead.

- **macOS**: `brew install python@3.12`, or download from python.org
- **Windows**: download from python.org and **tick "Add Python to PATH"** during install
- **Linux**: `sudo apt install python3.12 python3.12-venv`

On 3.10 the code itself runs, but pip has to fall back to older numpy, pandas
and scikit-learn releases, and you may hit wheel problems that have nothing to
do with this module. Not worth your time — install 3.12.

---

## Step 2 — Get an API key

### Option A — Gemini free tier (recommended)

1. Go to **aistudio.google.com/apikey**
2. Sign in with any Google account
3. Click **Create API key**
4. Copy it somewhere safe for a moment — you will paste it in step 4

Takes about two minutes. No card, no billing account.

### Option B — NVIDIA NIM

If you already have an NVIDIA developer account, or Gemini gives you trouble:

1. Go to **build.nvidia.com**, sign in, and generate an API key (starts `nvapi-`)
2. In `.env`, set `AIP_PROFILE=nvidia` and `NVIDIA_API_KEY=<your key>`

Fully verified — every lab runs on it. Two caveats worth knowing up front:
it is slower than Gemini (p95 ~16 s vs ~2.6 s on Lab 1), and it scores a few
points lower, so quote your own baseline rather than the published targets.
See `SETUP.md` for the numbers.

### Option C — fully offline, no key

Install [Ollama](https://ollama.com), then:

```bash
ollama serve            # leave this running in its own terminal
ollama pull llama3.1:8b
ollama pull llama3.2:3b
```

Everything in the module runs this way. It is slower, and Labs 1–2 will score
lower because small local models are weaker at structured output. That is a
legitimate choice and you will not be marked down for it — just say so in your
first lab report. You need about 8 GB of free RAM.

---

## Step 3 — Get the code and install

```bash
git clone https://github.com/subratpanda/ai-in-practice-1-module-1-students.git aip-module1
cd aip-module1
make setup
```

`make setup` creates a virtual environment in `.venv/` and installs everything
into it. **You do not need to activate it** — every `make` target finds `.venv`
on its own, which removes the most common setup failure there is.

If you want to run `python` directly rather than through `make`:

```bash
source .venv/bin/activate           # Windows: .venv\Scripts\activate
```

**`make setup` takes 5–15 minutes and downloads roughly 2 GB.** Most of that is
PyTorch, pulled in by `sentence-transformers`. It is genuinely needed — it is
what lets the retrieval labs run without spending money.

Do this on a decent connection, not on mobile data.

> **No `make` on Windows?** Do the same three steps by hand:
> ```
> python -m venv .venv
> .venv\Scripts\activate
> python -m pip install -r requirements.txt
> ```
> and use `python scripts/check_setup.py` in place of `make check` below.

---

## Step 4 — Add your key

```bash
cp .env.example .env
```

Open `.env` in any editor and set two lines:

```
AIP_PROFILE=gemini
GEMINI_API_KEY=<paste your key here>
```

Using Ollama instead? Set `AIP_PROFILE=ollama` and leave the key blank.

**`.env` is git-ignored.** Your key stays on your machine and will never be
committed. Do not paste it into Slack, a notebook, or a lab report.

---

## Step 5 — Check it

```bash
make check
```

**You are done when the last line reads `Environment is ready.`** It should look
like this:

```
AI in Practice I - Module 1: environment check

[  ok  ] python >= 3.10                     3.11
[  ok  ] import litellm                     litellm
[  ok  ] import pydantic                    pydantic
[  ok  ] import numpy                       numpy
[  ok  ] import chromadb                    chromadb
[  ok  ] import rank_bm25                   rank_bm25
[  ok  ] import sentence_transformers       sentence_transformers
[  ok  ] import dotenv                      dotenv
[  ok  ] AIP_PROFILE valid                  gemini
[  ok  ] GEMINI_API_KEY set                 ***abcd
[  ok  ] corpus present                     30 docs
[  ok  ] ticket data present                60 dev cases
[  ok  ] golden RAG set present             45 questions
[  ok  ] cache writable                     338 entries
[  ok  ] live model call                    'READY' in 940 ms
[  ok  ] embedding call                     dim=3072

Environment is ready.
```

Every line says `ok`, and it made one real call to a real model. That is the
whole test.

---

## If something fails

The check names the failing line and why. The most common four:

| It says | What happened | Fix |
|---|---|---|
| `GEMINI_API_KEY missing` | `.env` not created, or the key line is still blank | Redo step 4. Check you edited `.env`, not `.env.example` |
| `Dependencies are not installed` | `make setup` has not finished, or it installed into a different interpreter | Run `make setup`. Check `make help` — the last line tells you which Python it is using |
| `No module named ...` when running `python` directly | The virtualenv is not active | Either use `make` (which finds `.venv` for you), or `source .venv/bin/activate` — your prompt should then show `(.venv)` |
| `404 ... is no longer available` | A model name in the code has been retired by the provider | Run `python scripts/list_models.py` and bring the output to the setup session |
| First embedding call hangs for minutes | It is downloading a ~130 MB model, once | Let it finish. Instant after that |

`SETUP.md` has a longer troubleshooting table.

**Do not spend more than 20 minutes stuck.** Post on the course channel with the
exact output of `make check`, or bring the laptop to the setup session. Fighting
an installer is not what this module is teaching, and no marks depend on it.

---

## Recommended — check your key's headroom, 30 seconds

```bash
python scripts/check_rate_limit.py
```

Free-tier rate limits are **per key** and Google no longer publishes fixed
numbers for them, so the only way to know what yours does is to ask it. The
probe ramps concurrency, watches for 429s, and tells you which `--workers`
value to use in the labs.

**Nothing here is fatal.** The toolkit retries rate-limited calls with
exponential backoff and jitter, so a tight limit makes the labs slower, not
broken. This just tells you which one you are in for — and it is much better to
find out now than forty minutes into Lab 1.

If it reports fewer than 40 calls/min, say so on the course channel before the
lab and we will sort it out.

---

## Optional, if you finish early

Look at the data you will be working with. It is worth five minutes:

```bash
python -c "
import json, random
rows = [json.loads(l) for l in open('data/eval/extraction_dev.jsonl')]
for r in random.sample(rows, 3):
    print('=' * 70); print(r['expected']); print('-' * 70); print(r['input'])
"
```

These are the support tickets you will be extracting structured data from in
Lab 1 — forwarded email chains, WhatsApp messages, HTML fragments, Hinglish,
typos, shouting, signature blocks. Ask yourself what will make this hard. You
will be asked that question in the first session.

---

## Summary checklist

- [ ] Python 3.11+ installed (3.12 or newer preferred)
- [ ] API key created (or Ollama running)
- [ ] Repository cloned
- [ ] `make setup` completed
- [ ] `.env` created with `AIP_PROFILE` and your key
- [ ] `make check` ends with **`Environment is ready.`**

That is all. See you in Session 1.
