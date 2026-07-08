# MemPalace vs MemoryHub: Competitive Analysis

_Researched 2026-07-08. MemPalace v3.5.0 (v4.0.0-alpha imminent). MemoryHub v0.10.0._

## What They Are

**MemPalace** is a local-first AI memory system that stores verbatim conversation history and retrieves it via semantic search. It uses a spatial metaphor (wings/rooms/drawers) inspired by the Zettelkasten method. 57k GitHub stars, MIT license, Python 3.9+. Designed for individual developers using AI coding tools (Claude Code, Cursor, Codex CLI). Its philosophy: store everything verbatim, retrieve associatively, nothing leaves your machine unless you opt in.

**MemoryHub** is a Kubernetes-native agent memory system for OpenShift AI. It provides centralized, governed memory with OAuth 2.1, RBAC, multi-tenant isolation, and a tree-based memory model with branches (rationale, provenance). Designed for enterprise teams running shared agent infrastructure. Its philosophy: governed, multi-agent memory with curation, scope isolation, and audit trails.

## What MemPalace Has That We Don't

| Capability | Detail | Relevance to Us |
|---|---|---|
| **Verbatim storage** | Stores exact conversation text, never summarizes or paraphrases. 96.6% R@5 on LongMemEval | We store agent-curated memories, not raw transcripts. Our conversation threads (#168) store messages but focus on extraction, not verbatim recall. Different design choice, not a gap. |
| **Local-first / zero-API operation** | Runs entirely on-device with local embeddings (embeddinggemma-300m or MiniLM). No network calls required | We require a PostgreSQL cluster, vLLM serving, and MCP connectivity. Intentional for enterprise, but means we can't serve the solo-developer use case |
| **Spatial metaphor (wings/rooms/drawers)** | Hierarchical organization modeled on physical spaces. Scoped search within wings/rooms | Our tree model (nodes with branches) is more flexible but less intuitive as a mental model. Wings map roughly to our projects/scopes |
| **Pluggable storage backends** | ChromaDB (default), SQLite, Qdrant, pgvector. v4 adds LanceDB and PostgreSQL with pg_sorted_heap | We are pgvector-only by design. Pluggable backends aren't valuable for our use case (OpenShift clusters have PostgreSQL OOTB) |
| **On-device embedding models** | Ships embeddinggemma-300m (multilingual, 100+ languages) and all-MiniLM-L6-v2. No external service needed | We use vLLM-served MiniLM. We could offer local fallback but it conflicts with our centralized architecture |
| **GPU-accelerated local inference** | Docker GPU variant with CUDA-accelerated embeddings | Not relevant; our embeddings run on RHOAI vLLM serving which handles GPU scheduling |
| **Hybrid retrieval pipeline** | Keyword boosting, temporal-proximity boosting, preference-pattern extraction. Achieves 98.4% R@5 without LLM | Our retrieval is cosine + optional cross-encoder rerank + RRF focus blending. We don't have keyword fallback or temporal-proximity boosting |
| **Broad IDE integrations** | Auto-save hooks for Claude Code, Cursor, Codex CLI. Plugin directories for each | We integrate via MCP (any MCP client) and SDK/CLI, but don't ship IDE-specific auto-save hooks |
| **Agent diary system** | Each specialist agent gets its own wing and diary, discoverable at runtime | Our actor_id/driver_id model tracks agent identity but we don't have a diary concept |
| **LongMemEval benchmarks** | Published, reproducible retrieval benchmarks with committed per-question results | We have synthetic corpus benchmarks for the reranker but nothing published or standardized |
| **Massive community** | 57k stars, 7.4k forks, 263 open issues, active Discord | We have a handful of enterprise consumers (kagenti-adk) |

## What We Have That MemPalace Doesn't

| Capability | Detail | Why It Matters for Enterprise |
|---|---|---|
| **Multi-tenant RBAC** | OAuth 2.1, JWT-signed tokens, scope isolation (user/project/campaign/org/enterprise), tenant_id, OBO authorization | MemPalace has no auth model. Multi-user, multi-team memory requires access control |
| **Governance & audit** | Structured audit logging on all tool calls, actor_id/driver_id identity tracking, content moderation (quarantine/restore/hard-delete), legal hold, classified data spill response | MemPalace has no governance layer. Enterprise deployments need audit trails and incident response |
| **Curation pipeline** | Inline regex scanning, embedding dedup, entity extraction (spaCy NER with POLE+O), PII blocking, curation rules engine | MemPalace stores verbatim with no curation. Enterprise memory accumulates noise and PII without curation |
| **Curation agents** | Autonomous agents (Fact Checker, Trace Reviewer, Curator, Statistician) with Valkey queues and leader election | MemPalace has no autonomous curation. Stale and contradictory memories accumulate silently |
| **Memory tree model** | Memories have branches (rationale, provenance, checkpoint). Weight-based injection. Promotion across scopes | MemPalace uses flat drawers within a spatial hierarchy. No rationale branches, no provenance tracking |
| **Conversation threads** | First-class governed threads with retention policies, extraction pipeline, fork/handoff, A2A compatibility, 4-level deletion hierarchy | MemPalace stores raw transcripts but has no thread governance, retention enforcement, or extraction pipeline |
| **Temporal awareness** | `relevant_until` column, heuristic temporal classifier, search-time expiry filtering | MemPalace has time-decay scoring (roadmap) but no semantic expiry or temporal classification |
| **Content type system** | experiential/knowledge/behavioral classification, knowledge graduation workflow, `reconstruct` action for behavioral memories | MemPalace doesn't classify memory types |
| **Scope hierarchy** | user < project < campaign < role < organizational < enterprise with promotion workflow | MemPalace has wing-level scoping but no hierarchical scope model or promotion |
| **Campaign framework** | Cross-project knowledge sharing with enrollment-based RBAC | No equivalent in MemPalace |
| **Pattern surfacing** | Within-user pattern detection annotating search responses with `pattern_signals` | MemPalace has preference-pattern extraction in retrieval but no cross-memory pattern detection |
| **Dashboard UI** | React + PatternFly 6 with six panels, behind OAuth | MemPalace has no web UI |
| **Cross-encoder reranking** | ms-marco-MiniLM-L12-v2 with RRF focus blending, graceful cosine fallback | MemPalace uses LLM reranking (optional) but no cross-encoder |
| **Kubernetes-native deployment** | Three-namespace OpenShift topology, Alembic migrations, deploy/uninstall scripts, backup/restore | MemPalace deploys as a local tool or single Docker container |
| **SDK on PyPI** | Typed Python SDK with transparent OAuth, project config, extraction pipeline | MemPalace is CLI/MCP only, no programmatic SDK |
| **Platform integrations (designed)** | Kagenti, LlamaStack integration designs. kagenti-adk is a live consumer | MemPalace integrates with coding tools, not agent platforms |
| **Contradiction detection** | Report and resolve contradictions between memories | MemPalace has no contradiction handling |
| **Memory promotion** | Promote memories from narrower to broader scope with provenance | No equivalent |
| **Workflow checkpoints** | Durable key-value state for recurring agents via branch_type="checkpoint" | No equivalent |

## Head-to-Head on Shared Concerns

| Concern | MemPalace | MemoryHub | Edge |
|---|---|---|---|
| **Retrieval quality** | 96.6-98.4% R@5 on LongMemEval, published benchmarks | Synthetic corpus benchmarks only, no public numbers | MemPalace (published proof) |
| **Storage** | ChromaDB default, pgvector/Qdrant/SQLite/LanceDB options | pgvector only (PostgreSQL OOTB on OpenShift) | Depends on context |
| **Embedding** | Local models, no network needed | vLLM-served, requires cluster infra | MemPalace for simplicity, MemoryHub for scale |
| **MCP interface** | 35 tools | 3 tools (compact), 11 (full), 4 (minimal) | MemoryHub (compact profile is agent-friendly) |
| **Entity extraction** | v4 roadmap (local NLP, feature-flagged) | Shipped (spaCy NER, POLE+O, content-addressed IDs) | MemoryHub |
| **Privacy** | Local-first, nothing leaves machine unless opted in | Centralized server, OAuth-protected | MemPalace for privacy-sensitive solo use |
| **Multi-user** | Single-user by design | Multi-tenant with RBAC | MemoryHub |
| **Knowledge graph** | Temporal entity-relationship graph with validity windows (SQLite) | PostgreSQL-backed graph relationships, entity nodes | Comparable, different substrates |
| **Maturity** | v3.5.0, 1475 commits, 57k stars, 12 releases | v0.10.0, enterprise-focused, small user base | MemPalace (community), MemoryHub (enterprise features) |

## Why an OpenShift AI Cluster Operator Would Choose One Over the Other

### Choose MemoryHub When

- **Multiple teams share agents** and memory must be isolated by project, team, or tenant
- **Compliance requires audit trails**, PII blocking, content moderation, or legal hold
- **You're already on OpenShift** and want memory that deploys as a native component with PostgreSQL OOTB
- **Agents need governed memory** with RBAC, not just personal recall
- **You need curation at scale**: dedup, fact-checking, contradiction detection, pattern surfacing across users
- **Platform integration matters**: kagenti, LlamaStack, or custom agent frameworks via SDK
- **You want a dashboard** for administrators to monitor memory health, manage clients, and handle incidents
- **Memory has organizational value**: scope hierarchy lets individual agent learnings promote to team and org knowledge

### Choose MemPalace When

- **Individual developers** want personal AI memory for their coding sessions
- **Privacy is paramount**: nothing should leave the developer's machine
- **No cluster infrastructure** is available or justified for the use case
- **Raw recall quality** on conversation history is the primary goal (verbatim storage, proven benchmarks)
- **IDE integration** with Claude Code, Cursor, or Codex CLI is the entry point
- **You want something today** with a large community and MIT license

### They're Not Really Competitors

The honest answer is that these products serve different segments of the market:

- **MemPalace** is a developer productivity tool. It makes individual AI coding sessions smarter by remembering past conversations. It's the Zettelkasten for your AI pair programmer.

- **MemoryHub** is enterprise agent infrastructure. It makes organizational AI deployments governable by providing centralized, audited, multi-tenant memory with curation and scope isolation.

An OpenShift AI cluster could reasonably run both: MemPalace on developer workstations for personal coding memory, and MemoryHub on the cluster for shared agent memory with governance. They don't conflict.

The risk from MemPalace is indirect: if it adds lightweight multi-user features (their Qdrant and pgvector backends already support namespace isolation), it could creep into team use cases without the governance overhead that MemoryHub provides. The 57k-star community and MIT license make it a plausible "good enough" choice for teams that don't yet feel the pain of ungoverned shared memory.

## Gaps Worth Closing

Based on this comparison, areas where MemoryHub could learn from MemPalace:

1. **Published retrieval benchmarks**: MemPalace's LongMemEval numbers are a strong differentiator. We should benchmark against the same datasets and publish results.
2. **Keyword/hybrid search fallback**: Their hybrid pipeline catches exact-term queries that pure vector search misses. Worth evaluating for our retrieval path.
3. **Time-decay in search scoring**: Recency bias in retrieval is a simple win they're implementing in v4. Our temporal awareness is richer (semantic expiry) but doesn't do recency weighting.
4. **IDE auto-save hooks**: Their Claude Code / Cursor auto-save hooks are a nice developer experience. Our SDK extraction pipeline (#240) is more powerful but requires explicit integration.
5. **Local/offline fallback**: For disconnected or air-gapped environments, a local embedding fallback would extend our reach.
