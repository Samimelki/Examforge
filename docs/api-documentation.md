# API Documentation

Examforge uses **FastAPI**, which automatically generates interactive API documentation for all services.

## Access Documentation

### Swagger UI (Interactive)

Test endpoints directly in your browser:

- **Ingest Service**: http://localhost:7001/docs
- **Embed Service**: http://localhost:7002/docs
- **Retriever Service**: http://localhost:7003/docs
- **Exam-Engine Service**: http://localhost:7004/docs

### ReDoc (Alternative UI)

Read-only documentation with a clean interface:

- **Ingest Service**: http://localhost:7001/redoc
- **Embed Service**: http://localhost:7002/redoc
- **Retriever Service**: http://localhost:7003/redoc
- **Exam-Engine Service**: http://localhost:7004/redoc

### OpenAPI JSON Schema

Raw OpenAPI 3.0 specification:

- **Ingest Service**: http://localhost:7001/openapi.json
- **Embed Service**: http://localhost:7002/openapi.json
- **Retriever Service**: http://localhost:7003/openapi.json
- **Exam-Engine Service**: http://localhost:7004/openapi.json

## Usage

1. **Start services**:
   ```bash
   make dev-up
   ```

2. **Open Swagger UI** in your browser (e.g., http://localhost:7001/docs)

3. **Try it out**: Click "Try it out" on any endpoint, fill in parameters, and execute requests

## Features

- ✅ **Always up-to-date**: Generated automatically from your code
- ✅ **Interactive**: Test endpoints directly from the browser
- ✅ **No maintenance**: FastAPI handles everything
- ✅ **Type-safe**: Based on Python type hints and Pydantic models
- ✅ **Request/Response examples**: Auto-generated from your schemas

## Notes

- Documentation is generated at runtime from FastAPI decorators and type hints
- No static files needed - always reflects the current code
- Changes to endpoints are immediately visible after restarting the service
