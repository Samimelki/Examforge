# Examforge Compose Stack

Services: Traefik, Postgres, Redis, MinIO, Qdrant, OpenSearch, OpenSearch Dashboards, Ollama.

Prereqs: Docker Desktop (Apple Silicon supported).

1) Copy env files
- cp env.example .env
- cp infra/compose/env.example infra/compose/.env (optional)

2) Start stack (uses host Ollama by default)
- docker compose -f infra/compose/docker-compose.yml up -d

3) To run an internal Ollama container instead of host
- docker compose -f infra/compose/docker-compose.yml --profile internal-ollama up -d ollama
- Update OLLAMA_BASE_URL accordingly if you want to target the internal container (e.g., http://ollama:11434)

4) Verify
- Traefik: http://localhost:18080 (dashboard), http://localhost:10080 (web entrypoint)
- OpenSearch: http://localhost:9201
- Dashboards: http://localhost:5602
- Qdrant: http://localhost:6334
- MinIO: console http://localhost:9003, API http://localhost:9002
- Ollama: host at http://localhost:11434 (by default)

Notes
- Apple Silicon: Ollama uses Metal/MPS automatically.
- Memory: adjust OPENSEARCH_JAVA_OPTS if needed.
- For GPU servers later: enable GPU profile and runtime flags. Profiles keep portability.
