# AI in Practice I — Module 1: Applied GenAI

**Plaksha University · MS in Artificial Intelligence · Term 1**
27 contact hours · 4 theory lectures (6 h) + 7 problem labs (21 h)
**33 credit-equivalent hours** (theory counts double: 6 × 2 + 21 = 33)

---

## Start here

**New to the module?** Work through
[`PRE_MODULE_SETUP.md`](PRE_MODULE_SETUP.md) — 45 minutes, once.

```bash
make setup     # install
cp .env.example .env && $EDITOR .env     # one API key (free tier is fine)
make check     # verify -- you are ready when it prints "Environment is ready."
```

Then read [`SYLLABUS.md`](SYLLABUS.md) and [`SCHEDULE.md`](SCHEDULE.md), then
[`theory/T1`](theory/T1-anatomy-and-economics.md).

---

## What you build

Seven three-hour problems. Each one produces working code and a measured claim.

| | Lab | You build | You must prove |
|---|---|---|---|
| 1 | [The Reliable Extractor](labs/lab1/README.md) | Messy tickets → validated records | 100% schema validity, ≥ 0.95 field accuracy, under $0.15 |
| 2 | [The Prompt Lab](labs/lab2/README.md) | An experiment harness + a model cascade | A recommendation defended on quality × cost × latency, with a paired significance test |
| 3 | [Semantic Search That Works](labs/lab3/README.md) | Chunking, hybrid retrieval, reranking | nDCG@10 ≥ 0.80, and *why* dense beats BM25 on one query and loses on another |
| 4 | [RAG v1](labs/lab4/README.md) | Grounded answers with enforced citations | Citation validity 1.00, refusal precision *and* recall, judge κ ≥ 0.4 |
| 5 | [RAG v2](labs/lab5/README.md) | Diagnosis and a targeted fix | Every failure classified into one of 7 modes; a measured before/after |
| 6 | [Tools & Red-Teaming](labs/lab6/README.md) | A budgeted tool loop, then attack it | ≥ 0.80 block rate at ≤ 0.25 false positives, zero privileged calls |
| 7 | [Ship It](labs/lab7/README.md) | A deployed service with a CI regression gate | p95 SLO met, gate demonstrated failing, an honest evaluation report |

The four lectures — [T1](theory/T1-anatomy-and-economics.md),
[T2](theory/T2-specification-and-control.md),
[T3](theory/T3-evaluation-driven-development.md),
[T4](theory/T4-retrieval-engineering.md) — each unlock the labs that follow them.

---

## Everything here has been run

The targets in every lab handout are **measured, not estimated**. A reference
solution for all seven labs was written and executed against a live API;
before this module was finalised, and each lab handout carries the numbers it
achieved so you know what to aim at. Four of those results are deliberately
counter-intuitive and are taught as such:

- Few-shot prompting buys **nothing** on Lab 1's task (p = 1.00).
- The 4.8×-more-expensive model is **not detectably better** (p = 0.71).
- Hybrid BM25+dense retrieval **loses** to plain dense on this corpus.
- The Lab 5 reference fix **made the system worse** — and is reported as-is.

Two bugs found by running the materials are now written into the handouts as
war stories: a truncated LLM-judge verdict that reported faithfulness 0.667
when the true value was 0.933, and a response cache that silently defeated
self-consistency so a model cascade escalated 0% while appearing to work.

## The one rule

> **No number, no claim.**

"The prompt got better" scores zero. "Record accuracy 0.71 → 0.94 on the
120-item test split, at 1.8× cost and +340 ms p95" is a deliverable.

A negative result, honestly measured, scores full marks. Fabricated numbers
score zero for the lab.

---

## What this module assumes, and what it does not

**Assumed:** Python (from `Python Programming`), and the conceptual content of
`Introduction to Large Language Models and Generative AI` — transformers,
in-context learning, embeddings, the RAG paper. That course explains *how it
works*; this one makes it *work reliably*. See `SYLLABUS.md` §3 for the
contract between the two.

**Not assumed and not required:** model training, fine-tuning, GPUs, a cloud
account, or a paid API key.

---

## Cost

$0 to about $6 per student for the whole module. Free tiers (Gemini, Groq) and
a fully local path (Ollama) are supported and tested. A hard budget ceiling, a
response cache, and an offline replay mode are on by default. See `SETUP.md` §4.

---

## Repository

```
aip/           shared toolkit — read it, then modify it
theory/        four lecture notes (T1–T4)
labs/          seven handouts + starter code
data/          corpus, golden sets, tickets, attack suite
decks/         four .pptx lecture decks, generated from scripts/
docs/          the syllabus as .docx, for Academic Affairs
rubrics/       grading criteria
scripts/       setup check, deterministic data generation, document builders
tests/         unit tests
```

Everything binary is generated from a script (`make docs`), so the decks and
the Word syllabus stay reviewable in a diff and cannot drift from the Markdown.

Everything in `aip/` is under 250 lines per module and is meant to be read.
There is no framework hiding the interesting parts.
