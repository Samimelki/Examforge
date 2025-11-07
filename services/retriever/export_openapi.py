#!/usr/bin/env python3
"""Export OpenAPI spec without running the server."""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import app

if __name__ == "__main__":
    spec = app.openapi()

    # Try YAML output if available
    try:
        import yaml
        output_file = Path(__file__).parent / "openapi.yaml"
        with open(output_file, "w") as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
        print(f"✅ Exported to {output_file}")
    except ImportError:
        # Fallback to JSON
        output_file = Path(__file__).parent / "openapi.json"
        with open(output_file, "w") as f:
            json.dump(spec, f, indent=2)
        print(f"✅ Exported to {output_file}")
