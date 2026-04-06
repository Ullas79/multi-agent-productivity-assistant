#!/bin/bash
# entrypoint.sh – Container startup script for Cloud Run
# Runs any pre-start tasks then launches uvicorn

set -euo pipefail

echo "🚀 AgentFlow starting..."
echo "   Python: $(python3 --version)"
echo "   Port:   ${PORT:-8080}"
echo "   Region: ${REGION:-unknown}"

# Wait for DB to be reachable (Cloud Run startup grace period)
# AlloyDB via connector doesn't need an explicit wait; the connector handles it.

echo "✅ Starting Uvicorn..."
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --log-level info \
    --access-log \
    --no-server-header
