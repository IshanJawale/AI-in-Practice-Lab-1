# AI in Practice I — Module 1: Applied GenAI

**Plaksha University · MS in Artificial Intelligence · Term 1**
**Module 1 of the course `AI in Practice I` (2 Credits | 60 Lab Hours)**

| | |
|---|---|
| **Module hours** | 27 contact hours (6 theory + 21 lab) = **33 credit-equivalent hours** |
| **Format** | 4 × 1.5 h theory lectures, 7 × 3 h problem labs |
| **Cohort** | 27 students; ~11 fresh graduates, ~16 with ~2.7 years average experience |
| **Prerequisites** | Python Programming (Part 1); Introduction to Data Science (Maths & Stats) |
| **Co-requisite** | Introduction to Large Language Models and Generative AI |
| **Model training required** | None. All work uses pre-trained foundation models through APIs. |

---

## 1. What this module is

Module 1 is the **engineering** half of Generative AI.

The co-requisite course *Introduction to Large Language Models and Generative AI* teaches you
what a transformer is, why in-context learning works, what an embedding represents, and what
the RAG paper proposed. It answers **"how does this work?"**

This module answers a different question: **"how do I make this work reliably, cheaply, and
provably, for someone other than me?"**

Those are not the same skill. A student who can explain self-attention on a whiteboard and a
student who can ship a retrieval system that answers 92% of real questions with correct
citations for under a cent per query are two different people. Industry hires the second one.
Research labs increasingly do too, because a research idea you cannot evaluate is not a result.

Everything in this module is built on the same premise:

> **A GenAI application is a non-deterministic component inside a deterministic system.
> Your job as an engineer is to put enough structure, measurement, and fallback around
> that component that the system as a whole becomes trustworthy.**

## 2. What this module deliberately does *not* do

- **No model training, fine-tuning, or LoRA.** Pre-trained models via API only.
- **No transformer internals.** That is the LLM theory course. We treat the model as a
  probabilistic function with a price tag and a latency distribution.
- **No re-teaching of prompting basics.** You will have seen zero-shot / few-shot / CoT in
  the theory course. Here you *measure* them instead of describing them.
- **No autonomous multi-agent systems.** Module 1 stops at bounded, budgeted tool-use loops.
  Agentic systems belong to later modules.

## 3. Relationship to the LLM theory course

The two courses run in parallel. This table is the contract between them — read it so you
know what is expected to arrive from elsewhere.

| Concept | LLM theory course gives you | Module 1 makes you do |
|---|---|---|
| LLM APIs | Request/response format, decoding parameters | Provider abstraction, retries, rate limits, timeouts, caching, cost accounting, budget guards |
| Prompting | Zero-shot, few-shot, CoT, self-consistency | A/B a prompt portfolio against a golden set; report accuracy **and** cost **and** p95 latency; pick a winner with evidence |
| Structured output | JSON schemas, function-calling syntax | Schema-first design, Pydantic validation, repair loops, partial-failure handling, 95%+ field accuracy targets on messy real input |
| Embeddings | Distributional semantics, cosine similarity | Chunking strategy, index choice, hybrid BM25+dense fusion, reranking, recall@k / nDCG on a labelled query set |
| RAG | Pipeline diagram, chunk size, faithfulness | Diagnose *which of seven stages* is failing; fix it; prove the fix with a before/after eval |
| Tool use | Function calling, ReAct loop | Tool contracts, argument validation, budget caps, injection red-teaming, failure taxonomy |
| Evaluation | Precision/recall/F1, "check faithfulness" | Build the harness. Golden sets, LLM-as-judge with calibration, regression gates in CI |

If a lab asks you to do something the theory course has not covered yet, the lab handout
contains a self-contained primer. You are never blocked.

## 4. Course Learning Outcome mapping

Module 1 contributes to the parent course CLOs as follows.

| Parent CLO | Module 1 contribution |
|---|---|
| **CLO1 — Knowledge**: end-to-end AI system architecture | T1–T4 + Lab 7: the full serving path for a GenAI app — ingestion, index, inference, validation, observability, deployment |
| **CLO2 — Application**: apply techniques to build a working system | Labs 1, 3, 4, 6: extraction, search, RAG, tool use, all shipped as running code |
| **CLO3 — Analysis/Evaluation**: analyse performance, limitations, data quality | Labs 2, 5: eval harness construction, failure triage, measured improvement |
| **CLO4 — Creation/Synthesis**: complete system, problem → deployment | Lab 7: integrated, traced, cost-budgeted, deployed service with an evaluation report |

Program Learning Outcomes served: **PLO2** (design/develop/evaluate industry-grade systems)
and **PLO6** (end-to-end solutions) as primary; **PLO3** (MLOps practice) and **PLO4**
(deployment) as secondary.

## 5. Module Learning Outcomes

On completion of Module 1, a student can:

1. **MLO1** — Decompose a business problem into the parts a foundation model should handle
   and the parts deterministic code must handle, and justify the boundary.
2. **MLO2** — Specify an LLM task as a typed contract and enforce it with schema validation
   and repair, achieving a stated field-level accuracy target on messy input.
3. **MLO3** — Construct an evaluation harness with a golden set, and use it to choose
   between competing implementations on the joint axes of quality, cost, and latency.
4. **MLO4** — Build and tune a retrieval system: chunk, embed, index, fuse, rerank —
   and report standard IR metrics against a labelled query set.
5. **MLO5** — Diagnose which stage of a RAG pipeline is responsible for a wrong answer, and
   demonstrate a measured improvement.
6. **MLO6** — Apply engineering guardrails — budget caps, timeouts, input validation,
   prompt-injection defences, tracing — to a system exposed to untrusted input.
7. **MLO7** — Deploy the system behind an API with caching, streaming, and observability,
   and defend its behaviour with data.

## 6. Schedule

Nine 3-hour sessions. Theory precedes the lab it unlocks. Session-by-session
delivery notes, ordering constraints and cadence options: **`SCHEDULE.md`**.

| Slot | Session | Hrs | Title | Unlocks |
|---|---|---|---|---|
| 1 | **T1** | 1.5 | Anatomy & Economics of a GenAI Application | Lab 1 |
| 1 | **T2** | 1.5 | Specification & Control: Prompts as Programs, Schemas as Contracts | Lab 1 |
| 2 | **Lab 1** | 3 | **The Reliable Extractor** — messy text → validated records | |
| 3 | **T3** | 1.5 | Evaluation-Driven Development for Non-Deterministic Systems | Lab 2 |
| 3 | **T4** | 1.5 | Retrieval Engineering & the Seven Failure Modes of RAG | Labs 3–5 |
| 4 | **Lab 2** | 3 | **The Prompt Lab** — build the harness, then let it choose | |
| 5 | **Lab 3** | 3 | **Semantic Search That Actually Works** | |
| 6 | **Lab 4** | 3 | **RAG v1 — Grounded Answers with Citations** | |
| 7 | **Lab 5** | 3 | **RAG v2 — Diagnose, Fix, Prove** | |
| 8 | **Lab 6** | 3 | **Tool Use, Guardrails & Red-Teaming** | |
| 9 | **Lab 7** | 3 | **Ship It** — integration, deployment, demo day | |
| | **Total** | **27** | 6 h theory + 21 h lab · **33 credit-equivalent hours** | |

### Credit-equivalent hours

Under the University's credit convention, **one hour of theory is equivalent to
two hours of laboratory**. The module therefore carries:

| | Scheduled | Weight | Credit-equivalent |
|---|---|---|---|
| Theory (4 × 1.5 h) | 6 h | × 2 | **12 h** |
| Laboratory (7 × 3 h) | 21 h | × 1 | **21 h** |
| **Total** | **27 contact hours** | | **33 credit-equivalent hours** |

Against the parent course's 60 lab hours, Module 1 is **33/60 ≈ 55%** of
`AI in Practice I`, or approximately 1.1 of its 2 credits.

In credit-equivalent terms the laboratory-to-theory split is **21 : 12**, i.e.
1.75 : 1 — close to the 2:1 the brief asked for, and delivered without
sacrificing hands-on time. If an exact 2:1 is required, the clean way to reach
it is an eighth 3-hour lab (24 : 12 = 2 : 1, 30 contact / 36 credit-equivalent
hours); shortening the theory instead would mean 5.25 scheduled hours, which
does not divide into whole lectures. See `INSTRUCTOR_GUIDE.md` §2.

## 7. Assessment

Module 1 supplies the **Mid-course Presentation (50%)** component of the parent course.
Internal weighting:

| Component | Weight (of Module 1) | Assessed on |
|---|---|---|
| Lab deliverables, Labs 1–6 | 54% (9% each) | Working code + the required measurement, per lab rubric |
| Lab 7 capstone system | 20% | Deployed service, meets latency/cost budget, survives the red-team suite |
| Capstone evaluation report | 16% | A written argument, backed by your own harness, for why the system works |
| Engineering practice | 10% | Reproducibility, repo hygiene, cost discipline, honest negative results |

**A hard rule that applies to every lab:** a claim without a number is not a deliverable.
"The prompt got better" scores zero. "Field-level accuracy on the 120-item golden set rose
from 0.71 to 0.94, at 1.8× cost and +340 ms p95" is the deliverable.

**Honest negative results score full marks.** A lab in which you tried reranking, measured
it, found it made nDCG@10 *worse* on this corpus, and explained why, is a complete and
successful lab. Fabricated or unreproducible improvements score zero.

**Late policy and academic integrity** follow Plaksha University's Office of Academic Affairs
policy. On AI assistance specifically, see §9.

## 8. Tooling

| Layer | Choice | Why |
|---|---|---|
| Model access | **LiteLLM** unified client | One code path; students may bring Anthropic, OpenAI, Google, Groq, or a local Ollama model without editing lab code |
| Default tier | Small/cheap model for loops, mid model for quality | Enforced by `aip.config` model tiers; keeps per-student spend ≈ $0 – $6 |
| Zero-cost path | Google **Gemini** or **NVIDIA NIM** free developer tiers, or local **Ollama**, plus the shipped **response cache** | Every lab runs end-to-end with no billing account. Gemini and NVIDIA are both verified end to end |
| Structured output | **Pydantic v2** + provider JSON mode with a validation-repair loop | Provider-independent guarantees |
| Vector store | **ChromaDB** (local, embedded) | No server, no cloud account, no cost; `aip.retrieval` has a Qdrant adapter for scale-up |
| Lexical retrieval | **BM25** (`rank_bm25`) | The hybrid baseline that beats naive dense retrieval more often than students expect |
| Embeddings | Provider API **or** local `sentence-transformers` | Same offline story |
| Serving | **FastAPI** + Streamlit | Lab 7 |
| Tracing | Local JSONL traces via `aip.tracing` | No SaaS signup; optional Langfuse adapter |

Full install and API-key instructions: **`SETUP.md`**.

**All lab targets in this module are measured, not estimated.** A reference
solution for all seven labs was written and executed against a live API; the
results, including several counter-intuitive ones that are taught as findings,
are recorded in `solutions/MEASURED_RESULTS.md` (instructor copy).

## 9. Policy on using AI assistants in this module

You are training to build these systems. Using them is expected, not forbidden.

- **Allowed and encouraged:** using Claude/Copilot/Cursor for boilerplate, debugging,
  refactoring, and explaining errors.
- **Required:** you must be able to explain any line you submit. Labs are demoed live;
  the instructor will point at a line and ask why it is there.
- **Never allowed:** submitting evaluation numbers you did not generate by running the
  harness. This is fabrication of results and is treated as academic misconduct.

## 10. Reading

No textbook purchase required.

**Primary, per lab** — each lab handout lists 2–4 short readings (a doc page, a blog post,
a paper section). Total reading load ≈ 45 minutes per lab.

**Cross-referenced with the LLM theory course** — Jurafsky & Martin, *Speech and Language
Processing* (3rd ed. draft), Ch 5 (Embeddings), Ch 7 (LLMs), Ch 11 (IR and RAG).

**Standing references**
- Lewis et al. (2020), *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* — arxiv.org/abs/2005.11401
- Gao et al. (2023), *Retrieval-Augmented Generation for Large Language Models: A Survey* — arxiv.org/abs/2312.10997
- Es et al. (2023), *RAGAS: Automated Evaluation of Retrieval Augmented Generation* — arxiv.org/abs/2309.15217
- Zheng et al. (2023), *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* — arxiv.org/abs/2306.05685
- Greshake et al. (2023), *Not what you've signed up for: Indirect Prompt Injection* — arxiv.org/abs/2302.12173
- OWASP *Top 10 for LLM Applications* — owasp.org/www-project-top-10-for-large-language-model-applications
