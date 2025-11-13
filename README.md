# Examforge

AI-powered exam question generator using local LLMs and hybrid RAG for educational institutions.

## Overview

Examforge helps educators generate high-quality exam questions from curriculum materials (PDFs, presentations) using:

- **Local LLMs** (via Ollama) - No external API costs, complete privacy
- **Hybrid RAG** - Combines BM25 sparse search + dense vector embeddings with Reciprocal Rank Fusion
- **Evidence Validation** - Ensures generated questions are grounded in source material
- **Microservices Architecture** - Scalable, maintainable, independently deployable services

## Features

✅ **Document Ingestion** - Upload and parse PDFs/PPTX with GROBID (structure-aware) or pdfplumber
✅ **Hybrid Retrieval** - BM25 (OpenSearch) + Vector Search (Qdrant) with RRF fusion
✅ **Question Generation** - MCQ and SAQ generation via local LLMs
✅ **Evidence Validation** - Verbatim and paraphrased evidence detection (≥0.92 similarity)
✅ **Interactive UI** - Teacher interface for upload, generation, and review
🚧 **Question Bank** - CRUD operations for generated questions (Sprint 2)
🚧 **Student Interface** - Question-taking and assessment (Sprint 2-3)
🚧 **Evaluation Metrics** - Retrieval and generation quality metrics (Sprint 2)

## Quick Start

**Full setup guide:** [GETTING_STARTED.md](GETTING_STARTED.md)

```bash
# 1. Copy environment file
cp env.example .env

# 2. Pull required models
ollama pull nomic-embed-text
ollama pull llama3:8b

# 3. Start all services
make dev-up

# 4. Open Teacher UI
open http://localhost:3101
```

## Architecture

```
┌─────────────────┐
│   Teacher UI    │  React + Vite (TypeScript)
└────────┬────────┘
         │
    ┌────▼─────────────────────────────────────────┐
    │              API Gateway (Traefik)            │
    └────┬─────────┬──────────┬──────────┬─────────┘
         │         │          │          │
    ┌────▼────┐ ┌─▼──────┐ ┌─▼──────┐ ┌─▼─────────┐
    │ Ingest  │ │ Embed  │ │Retrieve│ │Exam-Engine│
    │ Service │ │Service │ │ Service│ │  Service  │
    └────┬────┘ └────────┘ └───┬────┘ └─────┬─────┘
         │                     │             │
    ┌────▼─────┐          ┌────▼────┐   ┌───▼──────┐
    │  MinIO   │          │ Qdrant  │   │  Ollama  │
    │PostgreSQL│          │OpenSearch   │  (Host)  │
    │  GROBID  │          │         │   └──────────┘
    └──────────┘          └─────────┘
```

**Services:**
- **Ingest** (7001): Document upload, parsing, chunking, indexing
- **Embed** (7002): Text embedding generation via Ollama
- **Retriever** (7003): Hybrid search with BM25 + vector + RRF
- **Exam-Engine** (7004): Question generation and evidence validation

**Infrastructure:**
- PostgreSQL: Document and chunk metadata
- MinIO: Object storage for uploaded files
- Qdrant: Vector database for dense embeddings
- OpenSearch: Full-text search with BM25
- GROBID: Structure-aware PDF parsing
- Ollama: Local LLM runtime (runs on host)

## Technology Stack

**Backend:**
- FastAPI 0.115.0
- Python 3.x
- PostgreSQL 16
- Qdrant v1.9.0
- OpenSearch 2.12.0
- MinIO (S3-compatible)

**Frontend:**
- React 18.2.0
- TypeScript 5.4.0
- Vite 5.4.2

**ML/AI:**
- Ollama (LLM runtime)
- nomic-embed-text (768-dim embeddings)
- llama3:8b (question generation)

**Infrastructure:**
- Docker Compose
- Traefik v2.10 (reverse proxy)

## Documentation

- **[Getting Started](GETTING_STARTED.md)** - Setup and installation guide
- **[API Documentation](docs/api-documentation.md)** - FastAPI auto-generated docs
- **[Architecture Decisions](docs/decisions.md)** - ADRs and key decisions
- **[Validation Checklist](docs/validation-checklist.md)** - Testing and validation
- **[Masterplan](Masterplan.md)** - High-level project goals and context
- **[Sprint Plans](Sprints.md)** - Development roadmap and tasks
- **[Changelog](CHANGELOG.md)** - Version history

## API Endpoints

### Services (Backend)

- **Ingest API**: http://localhost:7001/docs
- **Embed API**: http://localhost:7002/docs
- **Retriever API**: http://localhost:7003/docs
- **Exam-Engine API**: http://localhost:7004/docs

### UIs (Frontend)

- **Teacher UI**: http://localhost:3101
- **Student UI**: http://localhost:3002 (stub)

### Infrastructure

- **MinIO Console**: http://localhost:9003 (admin/adminadmin)
- **OpenSearch Dashboards**: http://localhost:5602
- **Qdrant Dashboard**: http://localhost:6334/dashboard
- **Traefik Dashboard**: http://localhost:18080

## Development

### Prerequisites

```bash
# Install Ollama
brew install ollama  # macOS
# or download from https://ollama.ai

# Pull models
ollama pull nomic-embed-text
ollama pull llama3:8b

# Start Ollama service
ollama serve
```

### Running Locally

```bash
# Start all services
make dev-up

# View logs
make logs

# Check service status
make ps

# Stop all services
make dev-down
```

### Making Changes

```bash
# Rebuild specific service after code changes
docker compose -f infra/compose/docker-compose.yml up -d --build ingest

# Or rebuild everything
make dev-down && make dev-up
```

## Project Structure

```
Examforge/
├── apps/
│   ├── teacher-ui/       # Teacher interface (React + TypeScript)
│   └── student-ui/       # Student interface (stub)
├── services/
│   ├── ingest/           # Document upload & parsing (FastAPI)
│   ├── embed/            # Embedding generation (FastAPI)
│   ├── retriever/        # Hybrid search (FastAPI)
│   └── exam-engine/      # Question generation (FastAPI)
├── infra/
│   ├── compose/          # Docker Compose configuration
│   └── models/           # Model registry and licenses
├── docs/                 # Documentation
├── seeds/                # Sample data for testing
├── .env                  # Environment configuration (gitignored)
├── env.example           # Environment template
├── Makefile              # Convenient commands
└── GETTING_STARTED.md    # Setup guide
```

## Key Design Decisions

From [docs/decisions.md](docs/decisions.md):

- **D-001**: Qdrant + OpenSearch over Postgres+pgvector (better BM25, easier hybrid tuning)
- **D-002**: Cross-encoder reranker enabled early (boost precision, reduce editorial burden)
- **D-003**: CPU-only (Apple Silicon) for pilot (M1 Max with Metal/MPS acceleration)
- **D-004**: Schema-per-tenant multi-tenancy (strong isolation, simpler data lifecycle)
- **D-005**: Evidence validation with paraphrases ≥0.92 similarity (balance trust with success rate)

## Roadmap

**Sprint 1** (Complete) ✅
- Infrastructure setup (Docker Compose, services, databases)
- Document ingestion and parsing
- Hybrid retrieval implementation
- Question generation with evidence validation
- Teacher UI implementation

**Sprint 2** (In Progress) 🚧
- Question bank with CRUD operations
- Evaluation metrics (retrieval quality, generation quality)
- Reranker integration (cross-encoder)
- UI polish and refinements

**Sprint 3** (Planned) 📋
- Student UI implementation
- Question export (PDF, DOCX, Moodle XML)
- Bulk operations and batch processing
- Multi-tenant setup and deployment

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run validation checklist
4. Submit a pull request

See [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) for PR guidelines.

## License

[Add license information]

## Credits

**Code Owner:** [@samimelki](https://github.com/samimelki)

**Built with:**
- [FastAPI](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.ai/)
- [Qdrant](https://qdrant.tech/)
- [OpenSearch](https://opensearch.org/)
- [GROBID](https://github.com/kermitt2/grobid)
- [React](https://react.dev/)

---

**Ready to get started?** → [GETTING_STARTED.md](GETTING_STARTED.md)
