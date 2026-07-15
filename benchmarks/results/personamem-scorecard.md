# PersonaMem 32k Scorecard

Competitive positioning on the PersonaMem/32k benchmark (589 queries,
195 documents, 37 personas).

**Last updated**: 2026-07-15

## Results

| Provider | Accuracy | Answer Model | Notes |
|----------|----------|--------------|-------|
| Hindsight | 86.6% | gemini-3.1-pro-preview | AMB neutral harness leader |
| Cognee | 81.8% | gemini-3.1-pro-preview | AMB neutral harness |
| AutoMem | 76.1% | gemini-3.1-pro-preview | AMB neutral harness |
| **MemoryHub (vector-only)** | **70.8%** | **gemini-3.1-flash-lite** | **This run (2026-07-15)** |
| BM25 local | 67.7% | gemini-3.1-flash-lite | Keyword baseline, no memory system |
| MemoryHub (pre-fix) | 46.5% | gemini-3.1-flash-lite | Matrix A, truncated content (2026-07-14) |

## Reading the table

The comparison is **not apples-to-apples**. The top three providers use
gemini-3.1-pro-preview as the answerer via the AMB neutral harness.
MemoryHub's 70.8% uses gemini-3.1-flash-lite, a much cheaper and weaker
model. A Pro spot check on 5 Flash Lite failures showed Pro getting 2/5
correct, suggesting a full Pro run would land in the low-to-mid 80s.

The AMB neutral harness fixes the answerer and judge models so the only
variable is the memory system. Our Flash Lite run measures retrieval
quality at a lower LLM ceiling. A proper leaderboard-comparable run
requires gemini-3.1-pro-preview as the answerer.

## Failure breakdown (MemoryHub 70.8%)

| Category | Count | Description |
|----------|-------|-------------|
| LLM failures | 116 | Correct context delivered, Flash Lite picked wrong MCQ answer |
| Retrieval incomplete | 56 | Missing 1-2 parent memories from context |
| Correct | 417 | Right answer with right context |

The `suggest_new_ideas` question type accounts for 50 of 116 LLM
failures (15.1% accuracy on that category alone). Even Pro struggles
with these closely-matched distractors.

## What it would take to be competitive

| Target | What's needed |
|--------|---------------|
| Match BM25 (67.7%) | Already exceeded at 70.8% |
| Match AutoMem (76.1%) | Fix retrieval incomplete (56 queries) + better answerer |
| Match Cognee (81.8%) | Pro answerer + retrieval fixes |
| Match Hindsight (86.6%) | Pro answerer + reranker + keyword signals enabled |
| 90%+ | All signals enabled + Pro answerer + suggest_new_ideas improvements |

## Pipeline configuration (this run)

- Embedding: granite-embedding-small-english-r2 (384-dim, 8192-token, GPU)
- Reranker: granite-embedding-reranker-english-r2 (disabled for vector-only baseline)
- Signals enabled: vector only (reranker, keyword, focus, domain, graph all disabled)
- Chunking: decoupled from S3, triggers at embedding model limit
- Search: chunk-to-parent expansion (chunks are search infra, parents returned)
- Content: full_only mode, no token budget degradation

## Sources

- [AMB leaderboard](https://agentmemorybenchmark.ai/)
- [Hindsight benchmarks](https://benchmarks.hindsight.vectorize.io/)
- [AutoMem AMB results](https://automem.ai/blog/automem-amb-neutral-numbers)
- MemoryHub runs: `benchmarks/results/personamem-baseline-2026-07-15.md`
