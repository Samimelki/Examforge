# Getting Started with Examforge

This guide will help you get Examforge up and running locally.

## Prerequisites

### Required

1. **Docker Desktop** (or Docker Engine + Docker Compose)
   - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Minimum: 8GB RAM allocated to Docker
   - Recommended: 16GB RAM

2. **Ollama** (for local LLMs)
   - [Install Ollama](https://ollama.ai/)
   - Must be running on host machine (not in Docker)

3. **Git**
   - For cloning the repository

### Optional but Recommended

- **Make** (for convenient commands)
- **Python 3.9+** (for running scripts outside Docker)
- **Node.js 20+** (for local frontend development)

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Samimelki/Examforge.git
cd Examforge
```

### 2. Set Up Environment

The `.env` file should already exist (copied from `env.example`). If not:

```bash
cp env.example .env
```

**Review `.env` and adjust if needed:**
- `OLLAMA_BASE_URL`: Should point to Ollama on your host machine
  - macOS/Windows: `http://host.docker.internal:11434` (default)
  - Linux: `http://172.17.0.1:11434` or your host IP

### 3. Pull Required Models

Download the models that Examforge uses:

```bash
# Embedding model (required)
ollama pull nomic-embed-text

# LLM for question generation (required)
ollama pull llama3:8b

# Alternative models (optional)
# ollama pull mistral:7b-instruct
```

**Verify Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

You should see a JSON response with your models listed.

### 4. Start All Services

```bash
make dev-up
```

This will:
- Build all Docker images
- Start infrastructure (Postgres, Redis, MinIO, Qdrant, OpenSearch, GROBID)
- Start application services (ingest, embed, retriever, exam-engine)
- Start frontend UIs (teacher-ui, student-ui)

**First startup takes 2-5 minutes** (downloading images, building, initialization).

### 5. Verify Services Are Running

Check service status:
```bash
make ps
```

All services should show `Up` status.

**Check service health:**
```bash
# Ingest service
curl http://localhost:7001/health

# Embed service
curl http://localhost:7002/health

# Retriever service
curl http://localhost:7003/health

# Exam-Engine service
curl http://localhost:7004/health
```

Each should return: `{"status":"ok"}`

---

## Access the Application

### Teacher UI (Main Interface)

**URL:** http://localhost:3101

**What you can do:**
- Upload PDF or PPTX files
- View service health status
- Ask questions and generate exam questions
- View retrieved passages and evidence validation

### Student UI (Stub)

**URL:** http://localhost:3002

Currently a stub implementation - planned for future sprints.

---

## Access Supporting Services

### API Documentation

Interactive Swagger UI for each service:
- **Ingest**: http://localhost:7001/docs
- **Embed**: http://localhost:7002/docs
- **Retriever**: http://localhost:7003/docs
- **Exam-Engine**: http://localhost:7004/docs

### Infrastructure Dashboards

- **Traefik Dashboard**: http://localhost:18080
- **MinIO Console**: http://localhost:9003
  - Username: `admin`
  - Password: `adminadmin`
- **OpenSearch Dashboards**: http://localhost:5602
- **Qdrant Dashboard**: http://localhost:6334/dashboard

---

## Testing the Application

### 1. Upload a Test Document

1. Go to http://localhost:3101
2. Verify all services show "ok" status
3. Upload a PDF (use `seeds/docs/sample.pdf` for testing)
4. Wait for parsing to complete
5. You should see: "Uploaded and parsed: X chunks"

### 2. Generate a Question

1. In the "Ask a question" field, enter a question related to your document
   - Example: "What are the main topics covered?"
2. Click "Ask"
3. Wait for generation (10-30 seconds depending on your hardware)
4. You should see:
   - An MCQ with 4 options
   - The correct answer highlighted in green
   - Evidence validation (verbatim/paraphrased/invalid)
   - Retrieved passages below

### 3. Verify the Fix

**This validates the critical bug fix we made:**

The question you typed should influence the generated question. Before the fix, the user's question was ignored.

**Test:**
- Ask: "What is machine learning?"
- Generated MCQ should be about machine learning
- Ask: "What is Python?"
- Generated MCQ should be about Python

If questions are relevant to your input, the fix is working! ✅

---

## Common Issues and Solutions

### Services won't start

**Check Docker resources:**
```bash
docker system df
docker system prune  # Clean up unused resources
```

**Check logs:**
```bash
make logs
```

### Ollama connection errors

**Verify Ollama is running:**
```bash
ollama list
```

**Check connectivity from Docker:**
```bash
docker run --rm curlimages/curl curl http://host.docker.internal:11434/api/tags
```

**Linux users:** Change `OLLAMA_BASE_URL` in `.env` to your host IP:
```bash
OLLAMA_BASE_URL=http://172.17.0.1:11434
```

### "Service unhealthy" in Teacher UI

**Wait 30 seconds** - services may still be starting up.

**Check individual service health:**
```bash
curl http://localhost:7001/health
curl http://localhost:7002/health
curl http://localhost:7003/health
curl http://localhost:7004/health
```

**View service logs:**
```bash
docker compose -f infra/compose/docker-compose.yml logs ingest
docker compose -f infra/compose/docker-compose.yml logs embed
```

### GROBID errors when parsing PDFs

GROBID is used for high-quality PDF parsing. If it fails, the system falls back to pdfplumber.

**This is normal and expected** - PDFs will still be processed, just with simpler extraction.

### Question generation is slow

**Expected times:**
- First request: 20-60 seconds (model loading)
- Subsequent requests: 10-30 seconds

**If slower than this:**
- Check CPU usage (Ollama is CPU-intensive without GPU)
- Try a smaller model: `ollama pull llama3.2:3b`
- Update `GEN_MODEL` in `.env`: `GEN_MODEL=llama3.2:3b`

---

## Development Workflow

### Making Code Changes

1. **Edit code** in `services/*/src/` or `apps/*/src/`

2. **Rebuild affected service:**
   ```bash
   docker compose -f infra/compose/docker-compose.yml up -d --build ingest
   ```

3. **Or rebuild everything:**
   ```bash
   make dev-down
   make dev-up
   ```

### Viewing Logs

```bash
# All services
make logs

# Specific service
docker compose -f infra/compose/docker-compose.yml logs -f ingest
```

### Stopping Services

```bash
# Stop all services
make dev-down

# Remove volumes (fresh start)
docker compose -f infra/compose/docker-compose.yml down -v
```

---

## Project Structure

```
Examforge/
├── apps/
│   ├── teacher-ui/       # React frontend for teachers
│   └── student-ui/       # React frontend for students (stub)
├── services/
│   ├── ingest/           # Document upload & parsing
│   ├── embed/            # Text embedding generation
│   ├── retriever/        # Hybrid search (BM25 + vector)
│   └── exam-engine/      # Question generation via LLM
├── infra/
│   ├── compose/          # Docker Compose orchestration
│   └── models/           # Model registry & licenses
├── docs/                 # Documentation
├── seeds/                # Sample data
└── .env                  # Environment configuration
```

---

## Next Steps

### For Users

1. Upload your own PDF documents
2. Generate questions from your content
3. Review evidence validation
4. Export questions (coming in Sprint 2)

### For Developers

1. Review [API Documentation](docs/api-documentation.md)
2. Check [Architecture Decisions](docs/decisions.md)
3. Read [Sprint Plans](Sprints.md)
4. Explore the [Masterplan](Masterplan.md)

### Planned Features (Sprint 2-3)

- Question bank with CRUD operations
- Evaluation metrics (retrieval quality, generation quality)
- Reranker integration for better precision
- Student UI implementation
- Question export to various formats

---

## Getting Help

### Documentation

- [API Documentation](docs/api-documentation.md)
- [Architecture Decisions](docs/decisions.md)
- [Changelog](CHANGELOG.md)

### Troubleshooting

1. Check service logs: `make logs`
2. Verify Ollama connection: `curl http://localhost:11434/api/tags`
3. Check service health endpoints
4. Review Docker resource allocation

### Support

- **Issues**: [GitHub Issues](https://github.com/Samimelki/Examforge/issues)
- **Code Owner**: @samimelki

---

## Clean Up

### Stop all services:
```bash
make dev-down
```

### Remove all data (fresh start):
```bash
docker compose -f infra/compose/docker-compose.yml down -v
```

### Remove all Docker images:
```bash
docker rmi $(docker images 'examforge/*' -q)
```

---

**Ready to start?** Run `make dev-up` and visit http://localhost:3101! 🚀
