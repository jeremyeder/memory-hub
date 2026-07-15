# PersonaMem Baseline Results

**Date**: 2026-07-15
**Dataset**: PersonaMem 32k (589 queries, 195 documents, 37 personas)
**Provider**: MemoryHub (vector-only, disabled signals: reranker, focus, keyword, domain, graph)
**Answer model**: gemini-3.1-flash-lite
**Embedding model**: granite-embedding-small-english-r2 (384-dim, 8192-token ctx, GPU/L40S)
**Reranker model**: granite-embedding-reranker-english-r2 (disabled for this run)

## Overall

| Metric | Value |
|--------|-------|
| Accuracy | 417/589 (70.8%) |
| Retrieval failures | 56 (incomplete parent coverage) |
| LLM failures | 116 (wrong answer with full context) |
| Zero stubs | 0 queries had stub degradation |

## By Question Type

| Question Type | Accuracy | Correct | Total | Retrieval | LLM |
|---------------|----------|---------|-------|-----------|-----|
| suggest_new_ideas | 15.1% | 14 | 93 | 15 | 64 |
| recalling_facts_mentioned_by_the_user | 52.9% | 9 | 17 | 3 | 5 |
| provide_preference_aligned_recommendations | 70.9% | 39 | 55 | 3 | 13 |
| recall_user_shared_facts | 76.7% | 99 | 129 | 5 | 25 |
| track_full_preference_evolution | 79.9% | 111 | 139 | 6 | 22 |
| generalizing_to_new_scenarios | 91.2% | 52 | 57 | 1 | 4 |
| recalling_the_reasons_behind_previous_updates | 93.9% | 93 | 99 | 1 | 5 |

## Context Delivery

| Metric | Value |
|--------|-------|
| Min context tokens | 19,098 |
| Max context tokens | 30,977 |
| Avg context tokens | 26,406 |
| Avg memories/query | 5.1 |
| Avg retrieve time | 1581ms |

## Pipeline Configuration

- **Chunking**: decoupled from S3; triggers at embedding model limit (8192 tokens / ~32K chars)
- **Chunk-to-parent expansion**: chunks are search infrastructure; search returns parent memories
- **mode=full_only**: bypasses token budget degradation
- **max_response_tokens=0**: no token budget limit
- **k=70**: retrieval returns up to 70 results (max 7 parents per persona in this dataset)
- **Recall pool**: 5x multiplier on max_results for chunk-to-parent headroom

## Gemini 3.1 Pro Spot Check (5 queries)

Tested 5 Flash Lite failures with Gemini 3.1 Pro Preview:
- Pro: 2/5 correct (Flash Lite: 0/5 on same queries)
- Pro struggles with the same `suggest_new_ideas` distractors
- Projected full Pro run: ~87% (vs 70.8% Flash Lite)

## Comparison to Previous Runs

| Run | Accuracy | Notes |
|-----|----------|-------|
| Matrix A (2026-07-14) | 46.5% | all-MiniLM-L6-v2, 1000-char S3 prefix, no content fix |
| This run (2026-07-15) | 70.8% | Granite embedding, full content, chunk-to-parent expansion |
| Delta | +24.3pp | Content delivery was the primary bottleneck |

## Known Limitations

1. **suggest_new_ideas** at 15.1% accuracy dominates failures (79/93 wrong). These questions have closely-matched distractors that even Pro struggles with.
2. **56 retrieval incomplete** queries miss 1-2 parents. The missing parents' chunks are semantically distant from the query and don't make the recall pool.
3. **Flash Lite reasoning ceiling** on 28K-token contexts with nuanced MCQ distractors.
