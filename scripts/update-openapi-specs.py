#!/usr/bin/env python3
"""
Update OpenAPI specs by directly exporting from FastAPI apps.
No need to run services - extracts specs from app definitions.
"""

import subprocess
import sys
from pathlib import Path

SERVICES = ["ingest", "embed", "retriever", "exam-engine"]

def update_openapi_specs():
    """Export OpenAPI specs from FastAPI app definitions."""
    print("📝 Updating OpenAPI specifications from FastAPI apps...\n")

    success_count = 0
    failed = []

    for service in SERVICES:
        print(f"📦 Exporting {service} spec...")

        script_path = Path(f"services/{service}/export_openapi.py")

        if not script_path.exists():
            print(f"❌ Export script not found: {script_path}\n")
            failed.append(service)
            continue

        try:
            # Run the export script in the service directory
            result = subprocess.run(
                [sys.executable, "export_openapi.py"],
                cwd=f"services/{service}",
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                print(result.stdout, end="")
                success_count += 1
            else:
                print(f"❌ Failed to export {service}:")
                print(result.stderr)
                failed.append(service)

        except subprocess.TimeoutExpired:
            print(f"❌ Timeout exporting {service}\n")
            failed.append(service)
        except Exception as e:
            print(f"❌ Error exporting {service}: {e}\n")
            failed.append(service)

        print()

    print(f"✨ Done! {success_count}/{len(SERVICES)} OpenAPI specs updated.")

    if failed:
        print(f"\n⚠️  Failed services: {', '.join(failed)}")
        return False

    return True

if __name__ == "__main__":
    success = update_openapi_specs()
    sys.exit(0 if success else 1)
