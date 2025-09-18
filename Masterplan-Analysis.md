## Examforge Masterplan — Technical Analysis and Recommendations

> Decisions reference: see `docs/decisions.md` — D-001 (Qdrant+ES/OS), D-002 (Reranker early), D-003 (Apple Silicon pilot), D-004 (Schema-per-tenant), D-005 (Paraphrase allowed)

### Executive summary
- **Vision strength**: Clear problem-solution fit for teacher-led content ingestion, retrieval-grounded generation, and adaptive student testing. Local-first constraint is feasible with modern open models and on-prem infra.
- **Primary risks**: Content quality/hallucinations, performance on commodity hardware, operational complexity of multi-service stack, and exam integrity (uniqueness and cheating mitigation).
- **Key recommendations**:
  - Add from Day 1: Postgres, Redis (queue), MinIO/S3 (object storage), and a reverse proxy (Traefik) in Compose alongside Qdrant and Elasticsearch.
  - Treat PDFs as immutable blobs in object storage; track normalized chunks + embeddings in DBs with strong IDs/provenance.
  - Enforce citation provenance mechanically: validate that EVIDENCE quotes occur verbatim or via fuzzy match in source text.
  - Standardize service contracts via OpenAPI, versioned, and add contract tests; add seed sample data and E2E tests early.
  - Keep KG/PathRAG for later; first harden hybrid retrieval (+ optional local reranker) and question editorial workflow.

---

### Product scope and personas
- **Personas**: Teachers (content owners/editors), Students (test-takers), Admin/IT (deployment/compliance).
- **Core flows**:
  1) Teacher uploads materials → system ingests → chunks → embeds → indexes.
  2) Teacher generates and curates questions tied to sources; saved in Question Bank with difficulty/topic metadata.
  3) Students practice or take exams with adaptive selection and unique variants; answers graded with provenance.

### Architectural overview (proposed)
- **Gateway**: Traefik routes to internal services; single external port.
- **Services** (FastAPI where Python is used): `ingest`, `embed`, `retriever`, `generator`/`exam-engine`, `frontend` (React/Vite). Later: `kg`.
- **Data plane**:
  - Object storage: MinIO (S3 compatible) for raw uploads and derived artifacts (JSON chunks, audit exports).
  - Relational DB: Postgres for metadata (documents, chunks, questions, exams, users, sessions, analytics).
  - Vector DB: Qdrant for dense embeddings.
  - Search: Elasticsearch/OpenSearch for sparse/BM25; alternative: Postgres full-text + pgvector for simpler ops (with fewer tuning features).
  - Queue: Redis for async/background jobs (parsing, embedding, re-indexing).
- **Observability**: Prometheus + Grafana (metrics), Loki or ELK for logs; OpenTelemetry tracing enabled early across ingest→embed→retrieve→generate.
- **Contracts**: OpenAPI specs for all services; shared schema/types where helpful.

### Local-first strategy
- **LLM runtime**: Ollama (prefer Mistral/Mixtral, Llama 3.1, Phi-4-mini) with quantized variants; auto-detect GPU and fall back to CPU.
- **Embeddings**: SentenceTransformers `all-mpnet-base-v2` (general) and PubMedBERT/BioClinicalBERT (domain). Use a pluggable registry and support dual embeddings per chunk (store both; select/weight at query time).
- **Reranking (optional but recommended)**: Use a cross-encoder reranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`). Avoid bi-encoders for reranking.

### Data modeling (initial)
- `documents(id, owner_id, title, source_uri, mime, status, created_at)`
- `document_versions(id, document_id, sha256, grobid_xml_uri, text_uri, created_at)`
- `chunks(id, document_version_id, ordinal, start_char, end_char, page, section_path, text_hash, text)`
- `embeddings(id, chunk_id, embedder_id, vector, dim, created_at)`
- `sparse_index(doc_version_id, chunk_id, es_index, es_id)`
- `questions(id, author_id, type, stem, metadata_json, citation_json, status, difficulty, topic_tags, created_at, updated_at, version)`
- `question_variants(id, question_id, version, payload_json, canonical, created_at)`
- `exams(id, course_id, name, settings_json, created_at)`
- `exam_sessions(id, exam_id, student_id, assigned_variant_ids, started_at, submitted_at, score)`
- `student_answers(id, session_id, variant_id, response_json, grading_json, correct, created_at)`
- `users(id, role, email, password_hash, created_at)` (replace with SSO later)

### Ingestion pipeline
- Accept uploads → store in MinIO with content hash path.
- Parse with `pdfplumber`; if PDF appears scanned, route to OCR (Tesseract) before text extraction.
- Extract structure with GROBID when available (sections, references, pages).
- Normalize into chunks (≈500 tokens with 50–100 overlap) with `section_path` and `page` metadata; maintain stable `chunk_id` using `document_version_id + ordinal`.
- Deduplicate near-identical chunks (minhash/SimHash) to avoid wasteful embedding.
- Emit events to queue: `document_parsed`, `chunks_ready` → embedding + indexing workers.

### PowerPoint ingestion (.pptx)
- Scope: Support `.pptx` in the same `ingest` service; no new core services required.
- Text extraction: use `python-pptx` to read titles, bullet text, tables, and speaker notes; persist `slide_index` and element type metadata.
- Images: optionally render slide images and extract embedded images; store to MinIO.
- OCR (optional): run Tesseract/PaddleOCR on slide images when enabled; store resulting `caption_text` with confidence.
- Captioning (optional): use a small local image captioning model when available; behind a feature flag due to CPU/GPU cost.
- Data model: extend with `slide_index`, `element_type` (title, bullet, note, table, image), `source_bbox` (optional), `image_uri`, `caption_text`.
- Retrieval: index titles/notes strongly; include `caption_text` as a lower-boosted field in Elasticsearch; embeddings remain text-only.
- Quality: apply thresholds to filter low-confidence OCR; prefer notes/context over generic captions for grounding.

### Retrieval strategy
- Hybrid retrieval: BM25 (ES) + dense (Qdrant).
- Merge via Reciprocal Rank Fusion; optionally follow with cross-encoder reranker.
- Return `top_k` passages with `doc_id:page:quote` and metadata; confidence score for UI and generator.

### Citation and provenance enforcement
- Require generator to output an `EVIDENCE` block: list of `doc_id:page:exact_quote`.
- Validate server-side with a pragmatic rule:
   1) Exact substring match in the cited chunk → accept.
   2) Else compute similarity (normalized Levenshtein or sentence-embedding cosine). If ≥ 0.92 → accept and tag as "paraphrased evidence".
   3) Else reject and regenerate with explicit instruction to quote verbatim.
- Ensure cited chunks were in retrieved context; log failures and expose them in the teacher UI.

### Question generation & quality
- Templates:
  - MCQ: stem, 1 correct, 3 distractors; shuffle on render; include rationale per option for later explanations.
  - SAQ: concise expected answer + rubric points.
- Metadata: difficulty (ELO-like), Bloom level, topic tags (curriculum taxonomy), source citations.
- Editorial workflow: teacher accepts/rejects/edits; version questions; never mutate approved canonical variant. Cache generation previews to reduce LLM runs; use teacher-edited pairs to fine-tune rerankers later.

### Cheating mitigation & uniqueness
- Per-student variant selection with parameterized randomization: option order, distractor sets, numeric perturbations where safe.
- Item exposure control: track usage frequency; throttle repeats.
- Near-duplicate detection across cohorts via shingling.

### Adaptive engine (initial)
- Start simple: per-topic proficiency score (ELO/Bayesian); update after each question.
- Bias sampling toward weak topics with guardrails to ensure coverage.
- Add spaced repetition for practice mode.

### Security, privacy, compliance
- On-prem by design; no external LLM APIs.
- Store minimal PII; encrypt at rest for storage/DB; audit logs for question edits and grading overrides.
- Consider FERPA/GDPR implications for student data; retention policies.
- Multi-tenancy: design tenant isolation early (separate schemas or per-tenant indexes) and plan SSO/OAuth for campus integration.
- Licensing: verify model licenses (Mistral/Mixtral, Llama variants) and document permitted usage under Ollama.

### Developer experience & repo strategy
- Monorepo is fine, but PNPM alone doesn’t manage Python. Use:
  - `turborepo` for task orchestration (optional),
  - `uv` or `poetry` for Python deps per service, and
  - `Makefile`/PNPM scripts as thin wrappers.
- Compose orchestrates: Traefik, Postgres, Redis, MinIO, Qdrant, Elasticsearch, services, and frontend.
- Standardize `.env` and `.env.example` for all services; single `dev-up` script.

### Testing strategy
- Unit tests per service; contract tests for OpenAPI compatibility.
- Integration test: upload → retrieve → generate → validate evidence.
- E2E via Playwright for teacher and student flows with seeded data.
- Add golden datasets and deterministic seeds for reproducibility. Establish a gold retrieval set and track Recall@k and MRR; make teacher-acceptance rate (target >70% in pilot) a primary product metric.

---

### Alignment with current sprints (proposed adjustments)

#### Sprint 1 (Core infra)
Add upfront:
- Postgres, Redis, MinIO, Traefik to Compose.
- Seed script and small sample PDFs and PPTX for demo/E2E.
- Ingest service should already persist uploads to MinIO and create `documents` rows (even if parsing is stubbed).
- Add `.pptx` path in `ingest`: extract titles/bullets/notes, persist `slide_index`, save originals to MinIO.
- Feature flags for OCR and captioning (disabled by default) to keep the pipeline extensible without performance penalties.
- Define OpenAPI contracts for `ingest`, `embed`, `retriever`, `generator` with mock responses; add contract tests.
- Basic observability (service health, request logs) and a single `dev-up` entrypoint.

Deliverable: upload a PDF or PPTX → appears in MinIO and DB → ask a question → pipeline returns stubbed answer with synthetic citations (validated format).

#### Sprint 2 (Ingestion & retrieval)
- Implement full parsing with pdfplumber + GROBID + OCR fallback.
- Enable `.pptx` OCR for slide images; persist `caption_text` and index it at lower boost than titles/notes.
- Tune slide-aware chunking: group bullets sensibly; tie notes to their slide chunks; dedupe and tokenize; persist to DB; emit jobs to Redis queues.
- Embedding service wraps SentenceTransformers; batch + rate-limit; store to Qdrant.
- Index chunks in ES with BM25; implement hybrid retrieval + RRF; optional local reranker.
- Optional: gate small local image captioning model behind a feature flag for image-heavy decks.
- Integration test returns top-5 real passages with metadata; add deletion/backfill flow.

#### Sprint 3 (Question generation)
- Promote `generator` to `exam-engine`; implement two templates (MCQ, SAQ).
- Enforce EVIDENCE block and server-side validation; auto-regenerate on failures.
- React UI for curation: generate → approve/reject/edit → save canonical question + variant(s) to DB.
- Endpoint to fetch teacher-approved questions; audit/versioning.

#### Sprint 4 (Student exam flow)
- Student auth (mock → JWT); select topic/subject.
- Practice/exam modes; variant randomization; MCQ auto-grading; SAQ rubric grading via local LLM.
- Adaptive selection using per-topic proficiency; analytics for teachers; uniqueness guarantees across students.

#### Sprint 5 (KG & PathRAG)
- Only after stability of retrieval/generation. Start with Neo4j + NER/RE pipeline; connect KG nodes to chunk IDs for provenance.
- Consider interim improvements (better rerankers) before KG complexity.

---

### Risks and mitigations
- **Hallucinations**: strict evidence validation; retrieval-only generation mode; rejection/regeneration loop.
- **Performance**: quantized models; batching; caching; precompute embeddings; optional GPU.
- **Operational complexity**: Compose profiles, Make targets, clear docs, small seed environment.
- **Search quality**: add reranker; improve chunking; fielded BM25; tune RRF weights.
- **Data sprawl**: object storage discipline; versioned documents; GC of stale artifacts.

### Recommended next steps
1) Update Sprint 1 with Postgres, Redis, MinIO, Traefik; write `.env.example` and `dev-up`.
2) Define OpenAPI contracts and mock responses; scaffold services with health checks.
3) Implement stub ingest writing to MinIO + DB; add seed PDFs.
4) Add Playwright E2E to prove the stubbed vertical slice end-to-end.

### Hardware guidance (pilot)
- For a smooth local experience: 24–32GB GPU (e.g., 3090/4090/A5000). Quantized 13B models perform well here.
- CPU-only fallback via ggml/llama.cpp is acceptable for small demos but slow; prefer GPU for pilot deployments.
