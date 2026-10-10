#!/usr/bin/env bash
# Deploy the static web app (web/) to Firebase Hosting. The API and AI stay on Cloud Run (scripts/deploy.sh);
# the app reads the Cloud Run URL from web/config.js and Cloud Run allows the Hosting origins (CORS).
# Usage: PROJECT_ID=breedernear-ai-2026 scripts/deploy_hosting.sh
# Auth: uses your gcloud Application Default Credentials (gcloud auth application-default login).
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PROJECT_ID:?Set PROJECT_ID, e.g. PROJECT_ID=breedernear-ai-2026}"
npx --yes firebase-tools@13.29.1 deploy --only hosting --project "$PROJECT_ID" --non-interactive
echo "Hosting: https://${PROJECT_ID}.web.app"
curl -fsS -o /dev/null -w "web app: %{http_code}\n" "https://${PROJECT_ID}.web.app/"
