# Lab 7 Evaluation Report

## 1. What it does
The Aurora Health RAG System allows policyholders and support agents to ask questions in plain English and receive accurate answers grounded in the company's official policy documents. It acts as an expert assistant that retrieves relevant clauses from the documentation and synthesizes them into an easy-to-read response, ensuring every claim is backed by a specific, verifiable document citation.

## 2. How well it works
The system was evaluated against a golden set of 45 queries (40 answerable, 5 unanswerable).

| Metric | Score | Target | Status |
|---|---|---|---|
| Correctness | 0.8625 | 0.80 | Pass |
| Faithfulness | 1.0000 | 0.95 | Pass |
| Citation Validity | 1.0000 | 0.98 | Pass |
| Refusal Recall | 1.0000 | 0.80 | Pass |
| Refusal Precision | 0.6250 | 0.60 | Pass |
| Hit Rate @ 5 | 0.9762 | 0.90 | Pass |

## 3. Where it fails
Based on our golden set evaluation, out of 45 questions, the system exhibits the following failure modes:
* **False Refusals (count: 3)**: The system incorrectly decides that it lacks sufficient information to answer questions like Q20, Q23, and Q42, returning "I don't have enough information in the provided sources to answer that." This results in a correctness score of 0 for these queries, and drags down the refusal precision to 62.5%.
* **Partial Answers / Missing Nuance (count: 5)**: For queries like Q04, Q11, Q26, Q32, and Q35, the system provides answers that are mostly correct but miss minor nuances or specific edge-case details, earning a partial correctness score of 1 rather than a perfect 2. For instance, it may provide the general rule but miss the exception for a specific tier of coverage if that detail wasn't prominently retrieved.

## 4. What it costs
* **Cost per query**: $0.0021
* **Cost per 1,000 queries**: $2.10
* **Cost per year (at 10,000 queries/day)**: $7,665.00

## 5. How fast it is
* **Overall p50 Latency**: 2.86 seconds
* **Overall p95 Latency**: 5.06 seconds

**Latency Breakdown by Stage (Seconds):**
| Stage | p50 | p95 |
|---|---|---|
| Input Guard | 0.02s | 0.03s |
| Embedding | 1.62s | 2.74s |
| Retrieval | 0.18s | 0.25s |
| Reranking | 0.01s | 0.01s |
| Generation (LLM) | 1.28s | 2.13s |
| Validation | 0.03s | 0.79s |

*Note: The embedding stage is the largest contributor to latency at p95, followed closely by the LLM generation phase.*

## 6. What it is not safe for
The system is **not safe for making definitive coverage or claim payout decisions**. It retrieves policy terms accurately (faithfulness = 1.0) but lacks patient-specific medical context and the authority to interpret ambiguous policy clauses. It should never be used as a final arbiter for medical necessity, pre-authorization, or claim approvals without human oversight. Furthermore, due to the false refusal rate (it occasionally plays it too safe and refuses to answer when the answer is present), it should not be relied upon as the *sole* source of information if a user is facing a critical emergency; human agents must remain accessible.

## 7. What you would do next
1. **Index/Chunking Optimization for Multi-Hop Queries (High Value)**: Tune the retrieval strategy (e.g. parent-document retrieval or adjusting chunk sizes) to reduce the false refusals. This will directly improve overall correctness and refusal precision, as false refusals currently account for our biggest point loss.
2. **Embedding Latency Optimization (Medium Value)**: Embedding takes up to 2.74s (p95). Switching to a faster embedding provider or self-hosting a smaller, faster embedding model would drastically cut our overall p95 latency and improve time-to-first-token (TTFT).
3. **Streaming Validation Improvements (Medium Value)**: While we implemented streaming, citations are evaluated at the end. We should explore optimizing the prompt or fine-tuning a small model to perform inline citation validation to avoid sending potentially invalid citations or text to the user before a refusal rollback is triggered.
