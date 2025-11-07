# Scripts

Utility scripts for the Examforge project.

## OpenAPI Spec Management

### `update-openapi-specs.py`

Updates the static OpenAPI YAML files by directly extracting specs from FastAPI app definitions.

**Key Feature:** No need to run services! Extracts OpenAPI specs directly from the code.

**Prerequisites:**
```bash
# Install PyYAML for YAML output (optional, will use JSON otherwise)
pip install pyyaml
```

**Usage:**
```bash
# Update all OpenAPI specs
make update-openapi

# Or run directly
python3 scripts/update-openapi-specs.py

# Or use bash version
./scripts/update-openapi-specs.sh
```

**How it works:**
1. Each service has an `export_openapi.py` script
2. Script imports the FastAPI `app` object
3. Calls `app.openapi()` to get the spec
4. Saves to `openapi.yaml` (or `openapi.json` if PyYAML not available)

**When to run:**
- After adding or modifying API endpoints
- Before committing API changes
- As part of CI/CD pipeline
- Enable pre-commit hook for automatic updates

### Per-Service Export Scripts

Each service has its own export script:
- `services/ingest/export_openapi.py`
- `services/embed/export_openapi.py`
- `services/retriever/export_openapi.py`
- `services/exam-engine/export_openapi.py`

You can run these individually:
```bash
cd services/ingest
python3 export_openapi.py
```

## Pre-Commit Hook

Optional hook to automatically update OpenAPI specs when service code changes.

**Enable:**
```bash
cp .githooks/pre-commit.example .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

**What it does:**
- Detects when files in `services/*/src/` are changed
- Automatically runs `make update-openapi`
- Warns if specs changed and need to be staged
- Prevents commit if validation fails

## Best Practices

1. **Always use automation**: Run `make update-openapi` after API changes
2. **Review diffs**: Check what changed in the OpenAPI files
3. **Commit together**: Commit code + OpenAPI specs in the same commit
4. **Enable pre-commit**: Use the hook to catch spec drift automatically
5. **FastAPI is truth**: The code is the source of truth, YAML files are generated
