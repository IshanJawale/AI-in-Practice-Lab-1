# Lab 3 — Semantic Search That Actually Works
### Note for students · read before the lab

> **In one line.** Everything you build in Labs 4 to 7 is capped by what
> retrieval finds — and this is the lab where you discover that published best
> practice is a prior, not a result.

> **Working through the lab?** [`CONCEPTS.md`](CONCEPTS.md) is the reference to
> keep open beside your editor — every concept the lab uses, what it is, where
> it sits in the code, and where it came from in the theory.
---

## Why this lab exists

Aurora's agents currently search policy documents with Ctrl-F. They type
*"how long do I have to file"*, the document says *"submitted within 30 days of
discharge"*, and they find nothing. That is the whole argument for semantic
search in one sentence, and you will see it as a specific measurable question
today (Q41: dense 1.00, BM25 0.00).

But the more valuable thing that happens in this lab is a contradiction.
T4 §4.3 calls hybrid retrieval *"the strongest single change most RAG systems
can make"*. On this corpus, hybrid **loses**. The cross-encoder reranker
**lowers** quality. The approximate index is **slower** than exact search.

None of those are mistakes in the theory. They are the theory meeting a
particular corpus, and learning to report what your data says rather than what
you were told to expect is the transferable skill in this lab. It will not be
the last time in your career that a well-established technique does nothing for
you.

**Where it sits.** Labs 4, 5 and 7 all sit on the retriever you choose today.
Choosing badly is recoverable; choosing without measuring is not, because you
will not know which stage to blame when Lab 4's answers are wrong.

---

## What you will build

- A **chunking sweep** across four strategies and three sizes, with the shape of
  the size curve explained rather than just reported
- A **retrieval comparison** — dense, BM25, hybrid — broken down **by question
  kind**, not just in aggregate
- A **reranking decision** with two different answers: one for an interactive
  search box, one for an overnight batch job
- A **metadata filter** that fixes three trap questions without touching the
  retriever at all
- A recommended configuration with all of its numbers

---

## How to approach it

**Do not grid-search.** Four chunkers × three sizes × three retrievers × three
rerankers × two indexes is 216 combinations and does not fit in three hours.
Sweep one axis, fix the winner, move on — and then say in your report what that
greedy procedure could miss.

**Write down the baseline before you change anything.** You will run
`--baseline` in the first fifteen minutes; that number is what every later
claim is relative to.

**Pick your metric before you run.** This is the trap of the lab and it is
easy to fall into: `hit_rate@5` is saturated on this corpus — every retriever
scores 0.93 to 0.98 — so it reports *nothing* while looking exactly like
"no difference". Use nDCG@10, recall@5, hit_rate@1 and MRR.

---

## Where this comes from in the theory

| Theory | What it claimed | Where you meet it today |
|---|---|---|
| **T4 §2.2** — the chunking trade-off | Bigger chunks dilute the embedding | Part A. The 400 / 800 / 1600 curve, and why it is not monotonic |
| **T4 §2.3** — the four strategies | Fixed, sliding, recursive, markdown-aware | Part A1. All four, measured, at the same size |
| **T4 §2.4** — what matters more than the model | Heading paths, metadata, parsing | A3 and D3 — both worth more than anything you do to the retriever |
| **T4 §3.2** — ANN | HNSW trades a little recall for a lot of speed *at scale* | Part D. At 164 vectors there is no scale to trade against |
| **T4 §4.1–4.2** — dense and BM25 | They fail on different questions | Part B. Q44 and Q41 are those two failures, isolated |
| **T4 §4.3** — hybrid / RRF | Usually the strongest single change | B5. Measure it here. Report what you measure |
| **T4 §4.4** — retrieve wide, rerank narrow | Two-stage retrieval buys ranking quality | Part C — at 131 ms, or at 28 seconds |
| **T3 §3.3** — retrieval metrics | Choose one with headroom | The whole lab. This is the saturated-metric lesson |

---

## Hints

- **If all four chunkers land within a point of each other, you have a bug, not
  a finding.** The usual cause is rebuilding the retriever while still reading a
  cached index. Print the chunk count — 83 against 164 is hard to fake.
- **The heading-path prefix lowers `hit_rate@5` while raising `hit_rate@1`.**
  That is not a contradiction. Work out which one it is improving and say so.
- **Break Part B down by question kind or you will see nothing.** The aggregate
  hides that dense and BM25 win on different subsets.
- **RRF's `k` will barely move anything.** Resist tuning it — the flatness is
  the finding, and chasing a 0.008 spread at n = 42 is fitting to noise.
- **The LLM reranker takes 28 seconds because it makes 30 calls in a row**, not
  because it is thinking hard. Ask what that means for your C3 answer.
- **Three questions have no relevant document** (Q36, Q38, Q39). Exclude those
  from retrieval metrics, and say in your report that you did — an unexplained
  n = 42 where the dataset says 45 reads as a mistake. (Five questions are of
  kind `unanswerable`; the other two do have relevant documents.)

---

## What separates a good report from an adequate one

- An adequate report gives the winning configuration. A good one gives the
  **per-kind breakdown** and explains the mechanism on Q44 and Q41 in two
  sentences each.
- An adequate report reports hybrid. A good one reports hybrid **honestly
  whichever way it lands**, with the count of questions where dense beat BM25.
- The C3 answer should be **two different deployments with two different
  answers**. If they are the same, that needs explaining.

---

## Questions we will discuss

1. Hybrid lost here and wins in most published results. What is different about
   this corpus? What would have to change for it to win?
2. The metadata filter fixed three questions for free and changed nothing about
   the retriever. Where else in your pipeline is there a data fix hiding behind
   a modelling problem?
3. Your greedy sweep fixed the chunker before choosing the retriever. Name a
   pair of axes in this lab that you suspect interact.
4. The LLM reranker is the best configuration measured and unusable
   interactively. If someone parallelised it to 1.5 seconds, would you deploy
   it? What else would you need to know?
