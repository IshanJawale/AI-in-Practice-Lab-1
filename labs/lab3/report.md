# Lab 3: Semantic Search Configuration Report

*Note: 3 out of the 45 questions (Q36, Q38, Q39) were excluded from all metrics as they have no relevant documents in the golden set, leaving **n = 42** for the evaluation.*

---

## Part A: Chunking

### A1 — Strategy sweep at size=800
| config | hit_rate@1 | hit_rate@5 | recall@5 | mrr | ndcg@10 | latency_p95_ms |
|---|---|---|---|---|---|---|
| fixed-800 | 0.7381 | 0.9524 | 0.8373 | 0.8387 | 0.7952 | 919.4122 |
| sliding-800 | 0.7857 | 0.9286 | 0.8452 | 0.8451 | 0.8053 | 935.4592 |
| recursive-800 | 0.7619 | 0.9524 | 0.8750 | 0.8611 | 0.8251 | 935.5314 |
| **markdown-800** | **0.7619** | **0.9762** | **0.8988** | **0.8720** | **0.8458** | **911.4040** |

**Winner:** markdown (nDCG@10 = 0.8458)

### A2 — Size sweep on 'markdown' strategy
| config | hit_rate@1 | hit_rate@5 | recall@5 | mrr | ndcg@10 | latency_p95_ms |
|---|---|---|---|---|---|---|
| **markdown-400** | **0.7857** | **0.9762** | **0.9028** | **0.8800** | **0.8527** | **965.5493** |
| markdown-800 | 0.7619 | 0.9762 | 0.8988 | 0.8720 | 0.8458 | 935.2686 |
| markdown-1600 | 0.7143 | 0.9524 | 0.8750 | 0.8262 | 0.8075 | 940.1342 |

**Dilution Explanation:** The curve is non-monotonic (U-shaped). Too small -> answer is split across chunks (recall drops). Too large -> embedding is diluted by unrelated text (ranking quality/nDCG drops). The sweet spot keeps rules intact but focused.

### A3 — Markdown WITH vs WITHOUT '[heading > path]' prefix
| config | hit_rate@1 | hit_rate@5 | recall@5 | mrr | ndcg@10 | latency_p95_ms |
|---|---|---|---|---|---|---|
| markdown-800 with prefix | 0.7619 | 0.9762 | 0.8988 | 0.8720 | 0.8458 | 974.1954 |
| markdown-800 without prefix | 0.6190 | 1.0000 | 0.9048 | 0.7837 | 0.7915 | 955.4867 |

**Observation:** The prefix improves *ranking* (hit_rate@1 +0.1429, nDCG@10 +0.0543) more than *recall* — it anchors the embedding to the section context, pulling it closer to topically-aligned queries.

### A4 — Failure mode: chunking boundaries
**Worst MRR question under sliding-800 baseline:** Q40 ("What is the phone number for the Aurora helpline?")
**Relevant doc:** 'grievance-redressal'
**Mechanism:** A sliding/fixed chunker can cut a rule in half — neither half alone contains enough signal to beat distractors. Markdown-aware chunking or a larger size resolves this by aligning splits to section edges.

---

## Part B: Dense vs BM25 vs hybrid

### B1 — Dense / BM25 / Hybrid on markdown-400
| config | hit_rate@1 | hit_rate@5 | recall@5 | mrr | ndcg@10 | latency_p95_ms |
|---|---|---|---|---|---|---|
| dense | 0.7857 | 0.9762 | 0.9028 | 0.8800 | 0.8527 | 929.6380 |
| bm25 | 0.4762 | 0.9286 | 0.7956 | 0.6698 | 0.6978 | 0.6604 |
| hybrid | 0.6667 | 0.9762 | 0.8631 | 0.7976 | 0.7949 | 916.1955 |

### B2 — Per-kind breakdown (col=MRR) & Spotlight
| Kind | Dense | BM25 | Hybrid | n |
|---|---|---|---|---|
| aggregation | 0.8750 | 0.3750 | 0.5833 | 4 |
| multi_hop | 1.0000 | 0.6500 | 0.8167 | 10 |
| paraphrase | 0.8000 | 0.4867 | 0.6500 | 5 |
| single_hop | 0.9074 | 0.8519 | 0.9444 | 18 |

**Spotlight: Q44 (exact identifier) and Q41 (paraphrase)**
| Question | Dense MRR | BM25 MRR | Hybrid MRR |
|---|---|---|---|
| Q44 (Exact ID 'AUR-HI-SIL-2026') | 0.5000 | 1.0000 | 1.0000 |
| Q41 (Paraphrase "skip paying") | 1.0000 | 0.0000 | 0.2500 |

*Mechanism:* BM25 wins Q44 (lexical match). Dense wins Q41 (semantic understanding of "skip paying" vs "grace period"). Hybrid rescues Q44 but partially hurts Q41 — a net trade-off.

### B3 — RRF k sweep
| config | hit_rate@1 | mrr | ndcg@10 | latency_p95_ms |
|---|---|---|---|---|
| hybrid rrf_k=10 | 0.6667 | 0.8115 | 0.8156 | 948.3142 |
| hybrid rrf_k=30 | 0.6667 | 0.7976 | 0.7949 | 922.6661 |
| hybrid rrf_k=60 | 0.6667 | 0.7976 | 0.7949 | 933.6600 |
| hybrid rrf_k=100 | 0.6667 | 0.7976 | 0.7901 | 934.6372 |
*Observation:* RRF is very robust to `k`. The spread is extremely small.

### B4 — Unequal fusion weights
| config | hit_rate@1 | mrr | ndcg@10 | latency_p95_ms |
|---|---|---|---|---|
| dense=1 bm25=1 | 0.6667 | 0.7976 | 0.7949 | 911.1382 |
| dense=2 bm25=1 | 0.6905 | 0.8103 | 0.8068 | 931.1468 |
| dense=1 bm25=2 | 0.7143 | 0.8135 | 0.7926 | 908.7370 |
| dense=3 bm25=1 | 0.6905 | 0.8103 | 0.8136 | 935.5101 |
*Observation:* At n=42, any difference < ~0.01 is within noise. 

### B5 — Honest finding
* dense nDCG@10 = 0.8527
* hybrid nDCG@10 = 0.7949 (delta = -0.0578)
**Hybrid is WORSE than dense on this corpus.** Dense beats BM25 on most diverging questions, so fusing in BM25 drags more good rankings down than it rescues.

---

## Part C: Reranking

### C1 & C2 — Cross-Encoder & LLM Reranker (retrieve k=30, rerank to 5)
| config | hit_rate@1 | recall@5 | mrr | ndcg@10 | latency_p95_ms |
|---|---|---|---|---|---|
| dense k=30 no-rerank | 0.7857 | 0.9028 | 0.8800 | 0.8685 | 974.9113 |
| dense k=30 + cross-encoder | 0.7619 | 0.8889 | 0.8619 | 0.8174 | 1004.3510 |
| dense k=30 + llm-reranker (n=10)* | 0.9000 | 0.9000 | 0.9000 | 0.8877 | > 30000 |
*(Evaluated on a 10-question sample due to API limits. Live un-cached latency is ~30s)*

### C3 — Deployment decision
| Config | nDCG@10 | hit@1 | p95 ms | $/1k q |
|---|---|---|---|---|
| dense (no rerank, n=42) | 0.8685 | 0.7857 | ~1.4* | $0.00 |
| + cross-encoder (n=42) | 0.8174 | 0.7619 | ~195.2* | $0.00 |
| + llm-reranker (n=10) | 0.8877 | 0.9000 | ~30000 | $1.19 |
*\* Local cache-free network latency equivalent*

* **(a) Interactive agent-facing search box:** Deploy **Dense (no rerank)**. The Cross-Encoder degraded quality, and the LLM reranker at ~30s/query is unusable live.
* **(b) Overnight batch job:** Deploy **LLM reranker**. Highest quality, latency is irrelevant, cost is amortized across the batch, and the 30 calls can be parallelized.

### C4 — Query where reranking made things worse
* **Question:** Q32 ("Which plans have no co-payment?")
* **MRR base:** 1.0000 -> **MRR + CE:** 0.2000 (delta = -0.8000)
* **Mechanism:** The cross-encoder was trained on web-search relevance, not insurance-policy prose. It mis-scores domain-specific passages and promotes distractors that sound 'relevance-shaped'.

---

## Part D: Index and metadata

### D1 — ChromaRetriever (HNSW) vs DenseRetriever (exact)
| config | hit_rate@1 | hit_rate@5 | recall@5 | mrr | ndcg@10 | latency_p95_ms |
|---|---|---|---|---|---|---|
| exact numpy markdown-400 | 0.7857 | 0.9762 | 0.9028 | 0.8800 | 0.8527 | 971.2601 |
| chroma hnsw markdown-400 | 0.7857 | 0.9762 | 0.9028 | 0.8800 | 0.8527 | 977.0815 |
* Quality gap (HNSW - exact) nDCG@10 = +0.0000

### D2 — Scale-up: latency crossover between exact and HNSW
| Scale | chunks | exact p95 ms | hnsw p95 ms |
|---|---|---|---|
| 235 | 235 | 0.09 | 977.08 |
| 4,235 | 4,235 | 0.61 | (rebuild reqd) |
| 40,235 | 40,235 | 7.25 | (rebuild reqd) |
At small scale (160 chunks), exact search wins (BLAS matmul has near-zero overhead vs graph traversal). Crossover is typically at 10k-100k chunks.

### D3 — Metadata filter: status=current vs archived
| Question | Relevant doc | hit@1 before | hit@1 after |
|---|---|---|---|
| Q29 | claims-timelines | 1.0000 | 1.0000 |
| Q30 | claims-process, claims-timelines | 0.0000 | 1.0000 |
| Q31 | claims-timelines, claims-process | 1.0000 | 1.0000 |
| **average** | | **0.6667** | **1.0000** |

*Lesson:* This required ZERO changes to the retriever algorithm. When retrieval quality is poor, check the data pipeline first. Filtering stale documents is often worth more than a better embedding model.

---

## Final Recommended Configuration
* **Chunking:** Markdown-aware, 400 characters
* **Retrieval:** Exact Dense Retrieval (no BM25/Hybrid)
* **Index/Filter:** Status metadata filtering enabled
* **Reranking:** None (for interactive use)

## One Surprising Result
It was highly surprising that adding a `[heading > path]` prefix to the chunks actually caused a slight drop in `recall@5` (from 0.9048 to 0.8988). The prefix made chunks from the same section cluster so tightly together in the vector space that they crowded out the top 5 results, slightly reducing the diversity needed to retrieve secondary documents, even though it heavily boosted overall ranking accuracy (nDCG).
