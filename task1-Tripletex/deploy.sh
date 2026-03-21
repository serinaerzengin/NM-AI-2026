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

# Deploy with API keys as env vars
gcloud run deploy tripletex-agent \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --concurrency 10 \
  --max-instances 5 \
  --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY,OPENAI_API_KEY=$OPENAI_API_KEY"

echo ""
echo "Done! Submit your URL at https://app.ainm.no/submit/tripletex"
