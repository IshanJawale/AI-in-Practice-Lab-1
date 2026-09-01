# Module 1 — Consolidated Grading Sheet

Module 1 supplies the parent course's **Mid-course Presentation (50%)**.

| Component | Weight of Module 1 |
|---|---|
| Labs 1–6 deliverables | 54% (9% each) |
| Lab 7 capstone system | 20% |
| Lab 7 evaluation report | 16% |
| Engineering practice (continuous) | 10% |

---

## Universal criteria — applied to every lab

These sit on top of each lab's own rubric and can move a grade a full band.

| | Excellent | Adequate | Unacceptable |
|---|---|---|---|
| **Evidence** | Every claim has a number from your own harness | Main claims quantified | "It seems better" |
| **Both sides** | Two-sided metrics reported in full (precision *and* recall; quality *and* cost) | One side reported, the gap acknowledged | One side reported as if it were the whole story |
| **Reproducibility** | Runs from a clean clone with `AIP_OFFLINE=1` | Runs with minor fixes | Cannot be reproduced |
| **Honesty** | Negative results and dev/test gaps reported unprompted | Reported when asked | Numbers that do not match the artefacts |
| **Split discipline** | Iterated on dev; test run once; gap reported | Test run more than once, disclosed | Tuned on test and reported test |

**Fabricated or unreproducible numbers score zero for the lab.** This is the
only automatic zero in the module and it is not negotiable.

**Honest negative results score full marks** in the analysis criterion of every
lab. "We tried X, measured it, it made things worse by N, here is why" is a
complete and successful outcome.

---

## Engineering practice (10%, assessed continuously)

| Criterion | Weight | Evidence |
|---|---|---|
| Repository hygiene | 25% | Meaningful commits; no secrets; no committed `.env`; runs from a clean clone |
| Cost discipline | 25% | Budgets used; cache used; total spend reported per lab |
| Code quality | 25% | Readable; the shared package used rather than copy-pasted; `ruff` clean |
| Reproducibility | 25% | Cache committed; `AIP_OFFLINE=1` works; seeds fixed where relevant |

---

## Per-lab weights

| Lab | Correctness / build | Method / discipline | Measurement | Analysis / argument |
|---|---|---|---|---|
| 1 Reliable Extractor | 25% | 20% boundary design + 20% reliability | 20% | 15% |
| 2 Prompt Lab | 20% harness | 25% experimental discipline | 20% statistics | 35% cascade + recommendation |
| 3 Semantic Search | 20% quality | 20% sweep discipline | 20% cost/latency | 40% diagnosis + metadata insight |
| 4 RAG v1 | 20% grounding | 20% refusal | 25% judge rigour | 35% decomposition + engineering |
| 5 RAG v2 | 20% fix quality | 15% prioritisation | 20% proof | 45% diagnosis + honesty |
| 6 Tools & Red-Team | 20% loop | 20% contracts | 20% both rates | 40% red-team rigour + survivability |
| 7 Ship It | see `labs/lab7/README.md` | | | |

---

## Band descriptors

**A (85–100).** The system meets its targets and the student can defend every
number. The report identifies a real limitation the rubric did not ask about.
At least one negative result is reported unprompted. Someone else could
reproduce the whole thing from the repository.

**B (70–84).** The system works and the required measurements are present and
correct. The analysis is accurate but stays inside what was asked. Minor gaps
in reproducibility or in two-sided reporting.

**C (55–69).** The system mostly works. Measurements are incomplete or reported
on one axis. The analysis restates the numbers rather than interpreting them.

**D (40–54).** Substantial parts do not run, or the numbers are present without
any argument. Test-split discipline broken without disclosure.

**F (< 40).** Not attempted, not reproducible, or numbers that do not match the
artefacts.

---

## Presentation assessment (Lab 7 demo day)

Five minutes per pair, live.

| | 2 | 1 | 0 |
|---|---|---|---|
| The system runs live | Yes, smoothly | With a hiccup they recover from | Does not run |
| Metrics shown are real | From `/metrics`, live | From a saved report | Asserted verbally |
| The refusal case is explained | Correct, and *why* refusal is right | Shown | Skipped |
| The regression gate fails on cue | Demonstrated | Described | Not built |
| **The worst remaining failure** | Named, diagnosed, with a next step | Named | "We don't have one" |
| Answers to questions | Confident and specific | Adequate | Cannot explain own code |
