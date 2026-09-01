# Module 1 — Session Schedule

11 booked slots × 3 hours. The module's content is **6 h theory + 21 h lab =
27 h**, which fills **9 slots exactly**. The remaining 2 slots are yours —
buffer, catch-up, or release them.

---

## The schedule

| Slot | Content | Theory | Lab |
|---|---|---|---|
| **1** | **T1** Anatomy & Economics of a GenAI Application (1.5 h)<br>**T2** Specification & Control (1.5 h) | 3 h | — |
| **2** | **Lab 1** — The Reliable Extractor | — | 3 h |
| **3** | **T3** Evaluation-Driven Development (1.5 h)<br>**T4** Retrieval Engineering & the 7 Failure Modes of RAG (1.5 h) | 3 h | — |
| **4** | **Lab 2** — The Prompt Lab | — | 3 h |
| **5** | **Lab 3** — Semantic Search That Actually Works | — | 3 h |
| **6** | **Lab 4** — RAG v1: Grounded Answers with Citations | — | 3 h |
| **7** | **Lab 5** — RAG v2: Diagnose, Fix, Prove | — | 3 h |
| **8** | **Lab 6** — Tool Use, Guardrails & Red-Teaming | — | 3 h |
| **9** | **Lab 7** — Ship It + Demo Day | — | 3 h |
| | **Total** | **6 h** | **21 h** |

27 contact hours · **33 credit-equivalent hours** (theory × 2: 12 + 21).

---

## Ordering constraints

**Hard — do not reorder:**

- Slot 1 (T1+T2) before Lab 1 — the labs assume the model/code boundary and
  schema-as-contract.
- Slot 3 (T3+T4) before Labs 2 and 3 — T3 is the eval harness, T4 is retrieval.
- Labs 3 → 4 → 5 in that order. Lab 4 uses Lab 3's retriever; Lab 5 reads
  `reports/lab4.json` and cannot start without it.
- Lab 7 last, and after Lab 6 — the service ships with the guardrails.

**Soft:** Lab 6 can swap with Lab 5. It needs Lab 4's pipeline, not Lab 5's fixes.

---

## Why theory is bundled into two slots

Each lab is designed as an unbroken 3-hour block with checkpoints at 45, 90 and
130 minutes. Putting 1.5 h of theory in front of a lab halves the lab, and the
half that goes is the part where students measure things — which is the part
being assessed.

Two 90-minute lectures back to back is a lot of talking, so take a real break
between them. The pairings are coherent: T1+T2 are both "what is this thing and
how do I pin it down", T3+T4 are both "how do I know if it works".

If you would rather interleave, the least damaging split is T3 in front of
Lab 2 and T4 in front of Lab 3, running those two labs at 1.5 h in-session with
the measurement finished as homework. It costs you the two checkpoints where
students are most likely to go quiet about being stuck.

---

## The two spare slots

Options, in the order I would use them:

1. **Buffer between Lab 4 and Lab 5.** The most likely place to run over —
   Lab 4's judge calibration is the step students underestimate.
2. **A second block for Lab 7.** It is the most over-specified lab in the
   module; a second slot lets Demo Day have its own room rather than competing
   with the CI gate for the last 45 minutes.
3. **A setup clinic before Slot 1.** Environment, keys, `make check`. If you
   skip it, expect to lose ~45 minutes of Lab 1 to `pip` — and it will be the
   same five students each time.
4. **Release them.**

---

## Cadence

| Cadence | Elapsed | Notes |
|---|---|---|
| **Twice weekly** | ~5 weeks | **Recommended.** Enough gap to write the report, not enough to forget the pipeline |
| Weekly | 9 weeks | Works, but context is lost between Lab 4 and Lab 5. Have students re-read their own `reports/lab4.json` before Lab 5 |
| Intensive (daily) | ~2 weeks | Viable and tiring. Reports become the bottleneck |

**Between-session load:** a 1–2 page report after each lab, plus 30–45 minutes
of reading before the next. Roughly 2 hours per session of independent work.
State this in week one.
