# Validation Checklist

This checklist validates the critical bug fixes applied to Examforge.

## Pre-Validation Setup

- [ ] `.env` file exists in project root
- [ ] Ollama is running: `curl http://localhost:11434/api/tags`
- [ ] Models are pulled: `ollama list` shows `nomic-embed-text` and `llama3:8b`
- [ ] Docker has at least 8GB RAM allocated

---

## Critical Fix #1: Service Dependencies

**Issue:** Ingest service could start before dependencies were ready, causing initialization failures.

**Fix:** Added `opensearch`, `embed`, and `grobid` to ingest service `depends_on`.

### Validation Steps

1. **Start services:**
   ```bash
   make dev-down
   make dev-up
   ```

2. **Watch startup logs:**
   ```bash
   make logs | grep -E "(ingest|opensearch|embed|grobid)"
   ```

3. **Expected behavior:**
   - OpenSearch starts first
   - Embed service starts
   - GROBID starts
   - Ingest service starts AFTER all dependencies
   - No "connection refused" errors in ingest logs

4. **Check result:**
   ```bash
   curl http://localhost:7001/health
   ```
   Should return: `{"status":"ok"}`

**Status:** [ ] PASS / [ ] FAIL

**Notes:**
_______________________________________________________

---

## Critical Fix #2: Missing Question Parameter

**Issue:** Teacher UI wasn't sending the user's question to exam-engine, resulting in generic questions.

**Fix:** Added `question: question` to the API request body in `apps/teacher-ui/src/main.tsx:112`.

### Validation Steps

1. **Open Teacher UI:**
   ```
   http://localhost:3101
   ```

2. **Upload a document:**
   - Use `seeds/docs/sample.pdf` or any PDF
   - Wait for "Uploaded and parsed: X chunks"

3. **Test Question Specificity:**

   **Test A - Specific topic:**
   - Ask: "What is machine learning?"
   - Click "Ask"
   - Generated MCQ should be about machine learning

   **Test B - Different topic:**
   - Ask: "What is Python?"
   - Click "Ask"
   - Generated MCQ should be about Python

4. **Expected behavior:**
   - Questions should relate to your query
   - Evidence should reference relevant passages
   - Different queries should produce different questions

5. **Old behavior (bug):**
   - Questions ignored user input
   - Generic questions regardless of query
   - Same question for different inputs

**Status:** [ ] PASS / [ ] FAIL

**Notes:**
_______________________________________________________

---

## Critical Fix #3: TypeScript Build

**Issue:** Missing `@types/react` and `@types/react-dom` caused TypeScript compilation failures.

**Fix:** Added type definitions to both UI `package.json` files.

### Validation Steps

1. **Rebuild teacher-ui:**
   ```bash
   docker compose -f infra/compose/docker-compose.yml build teacher-ui
   ```

2. **Check build logs for errors:**
   - No "Cannot find module 'react'" errors
   - No TypeScript compilation errors
   - Build completes successfully

3. **Rebuild student-ui:**
   ```bash
   docker compose -f infra/compose/docker-compose.yml build student-ui
   ```

4. **Expected behavior:**
   - Clean builds for both UIs
   - No missing type definition errors

**Status:** [ ] PASS / [ ] FAIL

**Notes:**
_______________________________________________________

---

## Critical Fix #4: TypeScript Configuration

**Issue:** Missing `tsconfig.json` files for proper TypeScript configuration.

**Fix:** Created `tsconfig.json` for both UIs with React + Vite settings.

### Validation Steps

1. **Verify files exist:**
   ```bash
   ls -la apps/teacher-ui/tsconfig.json
   ls -la apps/student-ui/tsconfig.json
   ```

2. **Check configuration:**
   ```bash
   cat apps/teacher-ui/tsconfig.json
   ```
   Should include:
   - `"jsx": "react-jsx"`
   - `"strict": true`
   - `"target": "ES2020"`

3. **Build verification:**
   - No warnings about missing tsconfig
   - TypeScript uses correct settings

**Status:** [ ] PASS / [ ] FAIL

**Notes:**
_______________________________________________________

---

## Critical Fix #5: CORS Standardization

**Issue:** Inconsistent `allow_credentials` settings across services (ingest: false, others: true).

**Fix:** Standardized all services to `allow_credentials=false`.

### Validation Steps

1. **Check each service:**
   ```bash
   grep -n "allow_credentials" services/*/src/app.py
   ```

2. **Expected output:**
   ```
   services/ingest/src/app.py:115:    allow_credentials=False,
   services/embed/src/app.py:12:    allow_credentials=False,
   services/retriever/src/app.py:14:    allow_credentials=False,
   services/exam-engine/src/app.py:16:    allow_credentials=False,
   ```

3. **Test CORS from browser:**
   - Open http://localhost:3101
   - Open browser DevTools > Network tab
   - Upload a document
   - No CORS errors in console

**Status:** [ ] PASS / [ ] FAIL

**Notes:**
_______________________________________________________

---

## Critical Fix #6: FastAPI Deprecation

**Issue:** Using deprecated `@app.on_event("startup")` in ingest service.

**Fix:** Migrated to modern `lifespan` context manager.

### Validation Steps

1. **Check for deprecation warnings:**
   ```bash
   docker compose -f infra/compose/docker-compose.yml logs ingest | grep -i deprecat
   ```

2. **Expected behavior:**
   - No deprecation warnings
   - Service starts cleanly

3. **Verify lifespan is used:**
   ```bash
   grep -A 5 "lifespan" services/ingest/src/app.py
   ```
   Should show `@asynccontextmanager` and `async def lifespan`

**Status:** [ ] PASS / [ ] FAIL

**Notes:**
_______________________________________________________

---

## Critical Fix #7: Dockerfile Optimization

**Issue:** Not copying `package-lock.json` before `npm install`, leading to non-reproducible builds.

**Fix:** Updated Dockerfiles to copy `package-lock.json*` along with `package.json`.

### Validation Steps

1. **Check Dockerfiles:**
   ```bash
   grep "package-lock" apps/teacher-ui/Dockerfile
   grep "package-lock" apps/student-ui/Dockerfile
   ```

2. **Expected output:**
   ```
   COPY package.json package-lock.json* ./
   ```

3. **Build and verify:**
   ```bash
   docker compose -f infra/compose/docker-compose.yml build --no-cache teacher-ui
   ```
   - Build uses exact versions from package-lock.json
   - Reproducible across different machines

**Status:** [ ] PASS / [ ] FAIL

**Notes:**
_______________________________________________________

---

## End-to-End Test

Complete workflow validation.

### Full Scenario

1. **Start fresh:**
   ```bash
   make dev-down
   docker compose -f infra/compose/docker-compose.yml down -v
   make dev-up
   ```

2. **Wait for all services** (check `make ps`)

3. **Upload document** via Teacher UI

4. **Generate question** with specific query

5. **Verify results:**
   - [ ] Question relates to query
   - [ ] 4 options displayed
   - [ ] Correct answer highlighted
   - [ ] Evidence validation shown
   - [ ] Retrieved passages displayed

6. **Check all service health:**
   ```bash
   curl http://localhost:7001/health
   curl http://localhost:7002/health
   curl http://localhost:7003/health
   curl http://localhost:7004/health
   ```
   All should return `{"status":"ok"}`

**Status:** [ ] PASS / [ ] FAIL

**Notes:**
_______________________________________________________

---

## Summary

| Fix | Status | Priority |
|-----|--------|----------|
| Service Dependencies | [ ] | Critical |
| Missing Question Parameter | [ ] | Critical |
| TypeScript Build | [ ] | Critical |
| TypeScript Configuration | [ ] | Critical |
| CORS Standardization | [ ] | High |
| FastAPI Deprecation | [ ] | High |
| Dockerfile Optimization | [ ] | Medium |
| End-to-End Test | [ ] | Critical |

**Overall Status:** _____________

**Date:** _____________

**Tester:** _____________

---

## Troubleshooting

### If Services Won't Start

```bash
# Check Docker logs
make logs

# Restart from scratch
make dev-down
docker compose -f infra/compose/docker-compose.yml down -v
make dev-up
```

### If Question Generation Fails

```bash
# Check Ollama connection
curl http://localhost:11434/api/tags

# Check exam-engine logs
docker compose -f infra/compose/docker-compose.yml logs exam-engine

# Verify retriever is working
curl -X POST http://localhost:7003/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

### If Tests Fail

1. Document the failure in Notes section
2. Capture relevant logs
3. Create an issue with reproduction steps
4. Reference this checklist in the issue
