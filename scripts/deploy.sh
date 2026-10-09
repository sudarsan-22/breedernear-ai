#!/usr/bin/env bash
# Deploy BreederNear AI to Cloud Run from source.
# Usage: PROJECT_ID=breedernear-ai-2026 scripts/deploy.sh
# See docs/implementation/05-gcp-setup-and-deployment.md for one-time setup.
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID, e.g. PROJECT_ID=breedernear-ai-2026}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-breedernear}"
MODEL="${BREEDERNEAR_MODEL:-gemini-3.8-flash}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"   # set to 1 from 17 Oct until results (rule R17)
SA="breedernear-run@${PROJECT_ID}.iam.gserviceaccount.com"
BUCKET="${PROJECT_ID}-breedernear-uploads"
GIT_SHA="$(git rev-parse --short HEAD)"

gcloud run deploy "$SERVICE" \
  --quiet \
  --project "$PROJECT_ID" \
  --source . \
  --region "$REGION" \
  --service-account "$SA" \
  --allow-unauthenticated \
  --min-instances "$MIN_INSTANCES" \
  --max-instances 1 \
  --session-affinity \
  --memory 1Gi --cpu 1 \
  --timeout 300 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_ENTERPRISE=True,GOOGLE_GENAI_USE_VERTEXAI=True,BREEDERNEAR_MODEL=${MODEL},BREEDERNEAR_BUCKET=${BUCKET},BREEDERNEAR_REGION=${REGION},GIT_SHA=${GIT_SHA}"

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
REVISION="$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format='value(status.latestReadyRevisionName)')"
echo "Deployed: $URL"
echo "Revision: $REVISION   (record the known-good revision for rollback)"
curl -fsS "$URL/api/health" && echo
