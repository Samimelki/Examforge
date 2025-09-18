## Examforge — Decisions Log

- Format: Each decision gets an ID, date, context, options, decision, rationale, and impact. When implemented, reference PRs.

### D-001: Retrieval/Search stack
- Date: 2025-09-17
- Context: Need sparse + dense retrieval for RAG. Options differ in ops complexity and features.
- Options:
  1) Qdrant (dense) + Elasticsearch/OpenSearch (sparse)
  2) Postgres + pgvector (dense) + Postgres FTS (sparse)
- Pros/Cons:
  - Qdrant + ES/OS
    - Pros: Best-in-class features for BM25, analyzers, hybrid tuning; Qdrant is fast and mature for vectors; clear separation of concerns.
    - Cons: Heavier ops (two external datastores); ES licensing/history; more moving parts.
  - Postgres + pgvector + FTS
    - Pros: Simpler ops; fewer services; transactional joins with metadata.
    - Cons: Less flexible BM25/analyzers; vector search less feature-rich; hybrid tuning is limited.
- Decision: Qdrant + Elasticsearch/OpenSearch
- Rationale: Chosen for pilot to maximize retrieval quality and tuning flexibility despite extra ops complexity.
- Impact: Compose includes Qdrant and ES/OS; retriever adapters implement hybrid RRF; evaluation baselines target BM25+dense.

### D-002: Cross-encoder reranker (enable now?)
- Date: 2025-09-17
- Context: Reranking improves precision@k; adds compute.
- Options:
  1) Enable from Sprint 2 (toggle)
  2) Defer until after hybrid baseline
- Pros/Cons:
  - Enable early
    - Pros: Better answer quality; de-risks retrieval.
    - Cons: Extra model/runtime; GPU preferred; latency.
  - Defer
    - Pros: Simpler infra; easier debugging.
    - Cons: Lower precision; more editorial burden.
- Decision: Enable from Sprint 2 (toggle)
- Rationale: Enable early to boost precision@k and reduce editorial load; keep behind a toggle; prefer GPU when available.
- Impact: Retriever service includes cross-encoder reranker path; Compose/LLM runtime configured accordingly; evaluation includes reranked metrics and latency budgets.

### D-003: Hardware for pilot
- Date: 2025-09-17
- Context: Affects model sizes and latency.
- Options:
  1) GPU node (24–32GB)
  2) CPU-only
- Pros/Cons:
  - GPU node
    - Pros: Fast generation/reranking; supports 13B quant models comfortably.
    - Cons: Higher cost; availability.
  - CPU-only
    - Pros: Cheapest to start; widest compatibility.
    - Cons: Slow generation; limits model/reranker choices.
- Decision: CPU-only (Apple Silicon optimized) for pilot; keep GPU-ready path
- Rationale: Develop on M1 Max MacBook Pro using Ollama with Metal/MPS acceleration and smaller quantized models; maintain a GPU Compose profile for future deployments.
- Impact: Default models are smaller (e.g., Mistral 7B quant) and cross-encoder may run CPU-side; configure Ollama for MPS; add optional GPU profile to Compose for later.

### D-004: Multi-tenancy strategy
- Date: 2025-09-17
- Options:
  1) Schema-per-tenant
  2) Row-level security (RLS) per tenant
- Pros/Cons:
  - Schema-per-tenant
    - Pros: Isolation; easier data export/delete.
    - Cons: Migration overhead; more admin.
  - RLS
    - Pros: Single schema; simpler migrations.
    - Cons: Riskier misconfig; perf considerations at scale.
- Decision: Schema-per-tenant
- Rationale: Prefer strong isolation and simpler tenant lifecycle (export/delete) for school deployments; accept extra migration/admin overhead.
- Impact: Migrations and DB tooling must support per-tenant schemas; indexing strategy and auth claims reflect tenant scoping.

### D-005: Evidence validation strictness
- Date: 2025-09-17
- Options:
  1) Verbatim-only
  2) Verbatim-or-paraphrase (≥0.92 similarity)
- Pros/Cons:
  - Verbatim-only
    - Pros: Strong teacher trust; easy auditing.
    - Cons: More generation retries; brittle.
  - Verbose-or-paraphrase
    - Pros: Flexible; fewer failures.
    - Cons: Slightly weaker guarantees; needs logging.
- Decision: Verbatim-or-paraphrase (≥0.92 similarity)
- Rationale: Balance teacher trust with practical generation success; accept high-similarity paraphrases and label accordingly.
- Impact: Generator templates include paraphrase guidance; server-side validator uses 3-step exact/fuzzy rule; metrics label paraphrased evidence.
