#!/usr/bin/env python3
"""
Script to update OpenAPI specs from running services.
Usage: python scripts/update-openapi-specs.py
"""

import json
import sys
import requests
from pathlib import Path

SERVICES = {
    "ingest": 7001,
    "embed": 7002,
    "retriever": 7003,
    "exam-engine": 7004,
}

def update_openapi_specs():
    """Fetch OpenAPI specs from running services and save to YAML files."""
    print("Updating OpenAPI specifications from running services...\n")

    success_count = 0
    for service, port in SERVICES.items():
        print(f"📝 Updating {service} service...")

        # Check if service is running
        try:
            health_resp = requests.get(f"http://localhost:{port}/health", timeout=2)
            if not health_resp.ok:
                print(f"⚠️  Service {service} not healthy on port {port}, skipping...\n")
                continue
        except requests.RequestException:
            print(f"⚠️  Service {service} not running on port {port}, skipping...\n")
            continue

        # Fetch OpenAPI spec
        try:
            spec_resp = requests.get(f"http://localhost:{port}/openapi.json", timeout=5)
            spec_resp.raise_for_status()
            spec = spec_resp.json()

            # Save to YAML (using JSON as intermediate format, can be converted to YAML)
            output_path = Path(f"services/{service}/openapi.yaml")

            # Try to use PyYAML if available
            try:
                import yaml
                with open(output_path, "w") as f:
                    yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
                print(f"✅ Updated {output_path} (YAML)\n")
            except ImportError:
                # Fallback to JSON if PyYAML not available
                output_path = Path(f"services/{service}/openapi.json")
                with open(output_path, "w") as f:
                    json.dump(spec, f, indent=2)
                print(f"✅ Updated {output_path} (JSON - install PyYAML for YAML output)\n")

            success_count += 1

        except requests.RequestException as e:
            print(f"❌ Failed to fetch OpenAPI spec from {service}: {e}\n")
            continue

    print(f"✨ Done! {success_count}/{len(SERVICES)} OpenAPI specs updated.")
    return success_count == len(SERVICES)

if __name__ == "__main__":
    success = update_openapi_specs()
    sys.exit(0 if success else 1)
