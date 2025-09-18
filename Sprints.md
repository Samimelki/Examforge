Sprint 1: Set up core infra.

> Decisions reference: see `docs/decisions.md` — D-001 (Qdrant+ES/OS), D-002 (Reranker early), D-003 (Apple Silicon pilot), D-004 (Schema-per-tenant), D-005 (Paraphrase allowed)

Tasks:
1. Create a new monorepo with PNPM workspaces (frontend, backend, services).
2. Add Docker Compose with Traefik + Postgres + MinIO + Redis + Qdrant + Elasticsearch/OpenSearch (or Postgres full-text+pgvector as a simpler alternative).
3. Scaffold FastAPI service "ingest" that accepts PDFs and PPTX (stub parsing for now). Persist uploads to MinIO and create `documents` rows.
4. Scaffold FastAPI service "embed" with a pluggable embedding registry (stub models). Define registry interface to support dual embeddings per chunk (general + domain) even if only one is active in Sprint 1.
5. Scaffold FastAPI service "retriever" that queries Qdrant + ES/OS (or pgvector) and returns dummy passages.
6. Scaffold FastAPI service "generator" that calls a local LLM via Ollama API (stub) and returns a response with an `EVIDENCE` block in `doc_id:page|slide:quote` format.
7. Scaffold a simple React frontend (Vite) with:
   - Teacher login (mock auth).
   - PDF/PPTX upload → calls ingest.
   - “Ask a question” → calls retriever → passes to generator → shows answer with citations.
8. Add a Makefile or pnpm scripts for `dev-up` (compose + frontend). Include `.env.example` for all services.
9. Observability and metrics: basic Prometheus metrics + request logging; enable OpenTelemetry traces across services.
10. Seed: add tiny gold retrieval dataset (few docs + known Q→chunk pairs) and a sample PPTX. Add a simple Recall@20 smoke test in dev.
11. Licensing: document selected local models and licenses (Ollama models) in the repo.

Keep everything containerized, with `.env` configs for ports and API keys.
At end, I should be able to upload a PDF or PPTX, ask a test question, and get a stubbed answer with fake citations, and see basic metrics.

Sprint 2: Implement ingestion and retrieval.

> Decisions: D-001, D-002 apply here.

Tasks:
1. Ingest service:
   - Use pdfplumber + GROBID for PDFs; add OCR fallback for scanned PDFs.
   - For PPTX: extract titles/bullets/notes; optional OCR on slide images; store `slide_index`, `element_type`, and `caption_text`.
   - Normalize into JSON chunks with metadata (doc id, page/slide, section). Tune slide-aware chunking.
   - Store in Postgres.
2. Embed service:
   - Wrap HuggingFace sentence-transformers with FastAPI.
   - Support at least two embedders: all-mpnet-base-v2 (general), PubMedBERT (domain).
   - Implement dual-embedding storage in Qdrant (separate payloads/collections) and allow query-time weighting.
3. Sparse index:
   - Store chunks in Elasticsearch/OpenSearch with BM25 enabled (or Postgres full-text if chosen).
   - Field boosts: titles/notes > body > caption_text.
4. Retriever service:
   - Implement hybrid retrieval (Qdrant + ES/OS or pgvector+FTS).
   - Merge candidates with Reciprocal Rank Fusion.
   - Add optional cross-encoder reranker toggle (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`).
   - Return top-K passages with metadata and provenance for generator.
5. Add chunking strategy (≈500 tokens + overlap for docs; smaller for slides); dedupe near-duplicates.
6. Tests & eval:
   - Integration test: upload doc → ask question → system returns top-5 real passages.
   - Evaluation scaffold: compute Recall@k and MRR on the gold set; record to metrics.

Output: end-to-end working hybrid retrieval pipeline with evaluation metrics.

Sprint 3: Question generation.

> Decisions: D-002, D-005 apply here.

Tasks:
1. Add "exam-engine" service (FastAPI) that:
   - Accepts passages + question type (MCQ, SAQ, vignette, oral).
   - Calls local LLM (Mixtral/Mistral via Ollama) with strict templates and caching for previews.
   - Enforces EVIDENCE block with citations: "doc_id:page|slide:quote".
   - Applies server-side evidence validation with the 3-step rule (exact match → accept; similarity ≥0.92 → accept as paraphrase; else reject/regenerate).
2. Implement 2 templates:
   - MCQ with 1 correct + 3 distractors.
   - SAQ (short-answer).
3. Add React UI for teachers:
   - Generate Q from a passage.
   - Accept/reject/edit → save into Question Bank (Postgres).
   - Versioning: preserve canonical variant; log edits.
4. Add endpoint to fetch teacher-approved Qs.
5. Metrics: track teacher-acceptance rate of generated questions; target >70% in pilot.
6. Licensing: verify and document model licenses; ensure compliance.

Integration test: ingest doc → teacher generates MCQ → system saves it with validated evidence and metrics recorded.
