#!/usr/bin/env bash
# Stream live Cloud Run logs to terminal.
# Usage: ./logs_stream.sh          (live tail)
#        ./logs_stream.sh last 50  (last N entries)

set -euo pipefail
source .env

PROJECT="${PROJECT:-ai-nm26osl-1813}"
SERVICE="tripletex-agent"

if [ "${1:-}" = "last" ]; then
    LIMIT="${2:-30}"
    gcloud logging read \
        "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE}\"" \
        --project "$PROJECT" \
        --limit "$LIMIT" \
        --format="value(timestamp,textPayload)" \
        | grep -v "LiteLLM\|litellm" \
        | grep -v "^$"
else
    echo "Streaming logs for ${SERVICE}... (Ctrl+C to stop)"
    gcloud logging tail \
        "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE}\"" \
        --project "$PROJECT" \
        --format="value(timestamp,textPayload)" \
        2>&1 | grep -v "LiteLLM\|litellm" | grep -v "^$"
fi
