# OpenAPI Documentation Sync Strategy

## Overview

Examforge maintains both **auto-generated** and **static** OpenAPI documentation:

- **Auto-generated** (source of truth): FastAPI automatically generates OpenAPI specs at runtime
- **Static files**: YAML files in `services/*/openapi.yaml` for version control and offline reference

## The Challenge

Static OpenAPI files can drift from the actual implementation. This document describes strategies to keep them in sync.

---

## Access Points

### Live Documentation (Always Current)

Each service provides auto-generated, always-current documentation:

| Service | Swagger UI | ReDoc | OpenAPI JSON |
|---------|------------|-------|--------------|
| Ingest | http://localhost:7001/docs | http://localhost:7001/redoc | http://localhost:7001/openapi.json |
| Embed | http://localhost:7002/docs | http://localhost:7002/redoc | http://localhost:7002/openapi.json |
| Retriever | http://localhost:7003/docs | http://localhost:7003/redoc | http://localhost:7003/openapi.json |
| Exam-Engine | http://localhost:7004/docs | http://localhost:7004/redoc | http://localhost:7004/openapi.json |

### Static Files (Version Controlled)

```
services/ingest/openapi.yaml
services/embed/openapi.yaml
services/retriever/openapi.yaml
services/exam-engine/openapi.yaml
```

---

## Sync Strategies

### ⭐ Option 1: Auto-Generate from Running Services (Recommended)

**How it works:**
1. Start services: `make dev-up`
2. Run sync script: `make update-openapi`
3. Review changes: `git diff services/*/openapi.yaml`
4. Commit if valid: `git add services/*/openapi.yaml && git commit`

**Pros:**
- Always accurate
- No manual maintenance
- Catches all changes automatically

**Cons:**
- Requires services to be running
- Extra step in workflow

**When to use:**
- After adding/modifying endpoints
- Before committing API changes
- During code reviews
- As part of CI/CD

**Setup:**
```bash
# Install dependencies
pip install pyyaml requests

# Update specs
make update-openapi
```

---

### Option 2: Pre-Commit Hook

Automatically check/update OpenAPI specs before each commit.

**Setup:**
```bash
# Enable pre-commit hook
cp .githooks/pre-commit.example .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

**How it works:**
- Detects when service code changes
- Automatically runs OpenAPI sync
- Warns if specs are out of sync
- Prevents commit if validation fails

**Pros:**
- Automated
- Catches drift early
- No manual steps

**Cons:**
- Requires services running locally
- Slightly slower commits
- May need to bypass for WIP commits

---

### Option 3: Remove Static Files

Use only auto-generated docs, remove static YAML files entirely.

**Implementation:**
```bash
# Remove static files
git rm services/*/openapi.yaml

# Update .gitignore
echo "openapi.yaml" >> .gitignore
```

**Pros:**
- No sync issues
- Less maintenance
- Always current

**Cons:**
- No offline API reference
- No version-controlled API history
- Harder to review API changes in PRs

---

### Option 4: Manual Sync (Not Recommended)

Manually update OpenAPI files when you remember.

**Pros:**
- Simple (no automation needed)

**Cons:**
- Error-prone
- Easy to forget
- Guaranteed drift over time
- Not scalable

---

## Recommended Workflow

### For Development

1. **Make code changes** to service endpoints
2. **Test locally**: Visit http://localhost:700X/docs
3. **Update specs**: Run `make update-openapi`
4. **Review diff**: Check what changed in the YAML files
5. **Commit both**: Code + OpenAPI specs together

### For Code Reviews

Reviewers should:
- Check if OpenAPI files are included in the PR
- Verify the OpenAPI changes match code changes
- Test endpoints using Swagger UI

### For CI/CD

Add to your pipeline:
```yaml
# GitHub Actions example
- name: Check OpenAPI Sync
  run: |
    make dev-up
    sleep 10  # Wait for services
    make update-openapi
    git diff --exit-code services/*/openapi.yaml || \
      (echo "OpenAPI specs out of sync" && exit 1)
```

---

## Best Practices

### ✅ DO

- **Use auto-generation** as the primary sync method
- **Run `make update-openapi`** before committing API changes
- **Review OpenAPI diffs** during code reviews
- **Keep FastAPI code** as the single source of truth
- **Add OpenAPI updates** to your definition of done

### ❌ DON'T

- Don't manually edit `openapi.yaml` files
- Don't commit code changes without updating specs
- Don't skip OpenAPI reviews in PRs
- Don't trust outdated static files

---

## Troubleshooting

### Services not running

```bash
# Start services
make dev-up

# Check status
make ps

# View logs
make logs
```

### PyYAML not installed

```bash
# Install PyYAML
pip install pyyaml requests

# Or use system package manager
# Ubuntu/Debian: apt install python3-yaml
# macOS: brew install pyyaml
```

### Specs still out of sync

```bash
# Force refresh
make dev-down
make dev-up
sleep 15  # Wait for full startup
make update-openapi
```

### Large diffs in OpenAPI files

This usually means:
- Endpoints were added/removed (expected)
- Endpoint signatures changed (review carefully)
- FastAPI version changed (check if intentional)

---

## Decision Log

**Decision**: Use auto-generation + static files (hybrid approach)

**Rationale**:
- Static files provide version history and offline reference
- Auto-generation ensures accuracy when needed
- `make update-openapi` is low-friction
- Pre-commit hook available for teams that want automation

**Alternatives considered**:
- Dynamic only: No version control history
- Manual sync: Too error-prone
- Pre-commit hook: Too disruptive for rapid iteration

**Review date**: Sprint 2 completion
