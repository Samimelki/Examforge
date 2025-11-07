#!/bin/bash
# Update OpenAPI specs from FastAPI app definitions
# No need to run services - extracts directly from code

set -e

SERVICES=("ingest" "embed" "retriever" "exam-engine")

echo "📝 Updating OpenAPI specifications from FastAPI apps..."
echo ""

success=0
total=${#SERVICES[@]}

for service in "${SERVICES[@]}"; do
    echo "📦 Exporting $service spec..."

    if [ -f "services/$service/export_openapi.py" ]; then
        if (cd "services/$service" && python3 export_openapi.py); then
            ((success++))
        else
            echo "❌ Failed to export $service"
        fi
    else
        echo "❌ Export script not found: services/$service/export_openapi.py"
    fi

    echo ""
done

echo "✨ Done! $success/$total OpenAPI specs updated."

if [ $success -eq $total ]; then
    exit 0
else
    exit 1
fi
