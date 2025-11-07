# Scripts

Utility scripts for the Examforge project.

## OpenAPI Spec Management

### `update-openapi-specs.py`

Updates the static OpenAPI YAML files from running services.

**Prerequisites:**
- Services must be running (`make dev-up`)
- Install PyYAML for YAML output: `pip install pyyaml requests`

**Usage:**
```bash
# Make sure services are running first
make dev-up

# Update OpenAPI specs
make update-openapi

# Or run directly
python3 scripts/update-openapi-specs.py
```

**What it does:**
- Fetches OpenAPI JSON from each service's `/openapi.json` endpoint
- Converts to YAML format
- Saves to `services/{service}/openapi.yaml`

**When to run:**
- After adding or modifying API endpoints
- Before committing API changes
- As part of CI/CD pipeline
- Periodically to catch drift

### `update-openapi-specs.sh`

Bash version of the OpenAPI update script. Requires `curl` and `python3` with PyYAML.

**Usage:**
```bash
./scripts/update-openapi-specs.sh
```

## Best Practices

1. **Keep specs in sync**: Run `make update-openapi` after modifying API endpoints
2. **Review changes**: Always review the diff of updated OpenAPI files before committing
3. **Source of truth**: The FastAPI code is the source of truth, not the YAML files
4. **Automation**: Consider adding to pre-commit hooks or CI/CD pipeline
