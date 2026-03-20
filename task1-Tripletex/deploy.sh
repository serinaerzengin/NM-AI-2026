#!/usr/bin/env bash
set -euo pipefail

# Load .env
set -a
source .env
set +a

echo "Deploying to Cloud Run in project: $PROJECT"
echo "Region: europe-north1"

# Authenticate if needed
gcloud config set project "$PROJECT"

# Deploy with GEMINI_API_KEY as env var
gcloud run deploy tripletex-agent \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY,LLM_MODEL=$LLM_MODEL"

echo ""
echo "Done! Submit your URL at https://app.ainm.no/submit/tripletex"
