# AI in Practice I · Module 1 · **Lab 1 — The Reliable Extractor**

Everything you need for Lab 1 is in this folder. Do the four items under
**Before the lab** *before* you walk in. They take about an hour and only the
first one needs a network.

---

## Before the lab — in this order

### 1 · Set up the environment — 15 min (plus download time)

```bash
make setup
```

Then get a free Google AI Studio key at **aistudio.google.com/apikey**, and:

```bash
cp .env.example .env
```

Open `.env` and put the key after `GEMINI_API_KEY=`. Leave `AIP_PROFILE=gemini`.

```bash
make check
```

**You are ready when the last line reads `Environment is ready.`**
If it does not, see *Troubleshooting* below, then `PRE_MODULE_SETUP.md`.

### 2 · Pydantic primer — 30 min, not optional

```bash
make primer
```

Eight exercises covering exactly the Pydantic surface Lab 1 uses. No API key,
no cost. **You are ready when it prints `8/8 passing`.**

Stuck on one? `python labs/lab1/pydantic_primer.py --solutions`. Reading an
answer and understanding it is fine. Skipping the file is not — if you meet
Pydantic for the first time during the lab, you will spend three hours on
syntax instead of on the actual problem.

### 3 · Read five tickets — 10 min

```bash
make tickets
```

**Write down three things you notice that will make this hard.** You will be
asked for them in the first ten minutes of the lab.

### 4 · Read the annotation guidelines — 15 min

`data/README.md`, the *Annotation guidelines* section. These are the rules the
labels were produced from. A label you cannot derive from a written rule is a
label nobody can hit. Pay attention to the `urgency` scale and the `complaint`
boundary — that is where most of the errors will be.

The *Known limitations* section at the end is worth five minutes too.

---

## What to read

| File | What it is |
|---|---|
| `labs/lab1/README.md` | **The brief.** Problem, targets, parts A–D, deliverables, rubric. |
| `labs/lab1/RUNSHEET.md` | **The step-by-step.** Keep this open during the lab. |
| `data/README.md` | The annotation guidelines. Required. |
| `theory/T1-*.md`, `T2-*.md` | The theory this lab is built on. |
| `decks/*.html` | The T1 and T2 slides. Open in any browser. |
| `rubrics/MODULE1_GRADING.md` | How it is marked. |

## What you run and edit

| File | What you do |
|---|---|
| `labs/lab1/pydantic_primer.py` | Run before the lab. 8/8. |
| `labs/lab1/v0_naive.py` | Part A. **Run it, do not fix it.** |
| `labs/lab1/extract.py` | **The only file you edit.** Parts B and C. |
| `labs/lab1/run_eval.py` | The harness. Read it, then use it. |

`aip/` is the shared library. Read it — especially `aip/llm.py` — but do not
change it.

---

## Troubleshooting

Work down this list. Most problems are one of the first three.

### `make: python: No such file or directory`

You are on a Mac or Linux box where `python` does not exist, only `python3`.
The Makefile handles this now — if you still see it, your copy is stale.
Workaround that always works:

```bash
python3 -m venv .venv && ./.venv/bin/python -m pip install -r requirements.txt
```

### `make setup` fails on your Python version

You need **Python 3.11 – 3.14**. Check with `python3 --version`.

- **Too old (3.10 or below):** current numpy/scipy will not build. Install 3.12
  or 3.13 — `brew install python@3.13` on macOS, `apt install python3.13-venv`
  on Ubuntu, or python.org on Windows.
- **Too new (3.15+):** litellm does not support it yet. Install 3.13 alongside.

Then point the venv at the right one explicitly:

```bash
python3.13 -m venv .venv && make setup
```

### `ModuleNotFoundError: No module named 'litellm'` (or pydantic, chromadb…)

The dependencies went into a different interpreter than the one running your
code. You do **not** need to activate the venv for `make` targets — they find
`.venv` on their own. If you are running `python` directly, either activate it:

```bash
source .venv/bin/activate
```

…or call the venv's interpreter by path: `./.venv/bin/python labs/lab1/…`

To confirm which interpreter `make` is using: `make help` prints it on the last
line.

### `make check` says `GEMINI_API_KEY set` is FAIL

`.env` is missing, is in the wrong directory, or the key line is malformed.
It must be in the repo root, and the line must be `GEMINI_API_KEY=AIza...`
with **no quotes and no spaces** around the `=`.

### `make check` fails on the live model call — 404 / model not found

Model IDs change. Run:

```bash
python scripts/list_models.py
```

…and tell the instructor what it prints. Do not try to guess a replacement.

### `make check` fails on the live model call — 429 / rate limited

The free tier is per-key and per-minute. Wait sixty seconds and retry. If it
persists, switch to the NVIDIA fallback: get a key at **build.nvidia.com**,
set `NVIDIA_API_KEY=nvapi-...` and `AIP_PROFILE=nvidia` in `.env`.
(Lab 1's published target numbers were measured on Gemini, so use Gemini if
you can and treat NVIDIA as the backup.)

### `pip install` is very slow or fails on `sentence-transformers`

It pulls PyTorch, which is large. Give it time and a decent connection. This is
the single reason to do setup the night before rather than in the room.

### Windows

Use PowerShell, not cmd. If `make` is unavailable, run the commands directly:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts\check_setup.py
```

### Still stuck after ten minutes

Stop and ask on the course channel. Paste the **exact** command and the **full**
error. Do not spend the lab session on setup — that is not what is being
assessed, and it is not what you are here for.
