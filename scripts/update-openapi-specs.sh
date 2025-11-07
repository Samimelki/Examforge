#!/bin/bash
# Script to update OpenAPI specs from running services
# Usage: ./scripts/update-openapi-specs.sh

set -e

SERVICES=("ingest:7001" "embed:7002" "retriever:7003" "exam-engine:7004")

echo "Updating OpenAPI specifications from running services..."
echo ""

for service_port in "${SERVICES[@]}"; do
    IFS=':' read -r service port <<< "$service_port"

    echo "📝 Updating $service service..."

    # Check if service is running
    if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
        # Fetch OpenAPI JSON and convert to YAML
        curl -s "http://localhost:$port/openapi.json" | \
            python3 -c "import sys, yaml, json; yaml.dump(json.load(sys.stdin), sys.stdout, default_flow_style=False, sort_keys=False)" \
            > "services/$service/openapi.yaml"

        echo "✅ Updated services/$service/openapi.yaml"
    else
        echo "⚠️  Service $service not running on port $port, skipping..."
    fi

    echo ""
done

echo "✨ Done! OpenAPI specs updated."
