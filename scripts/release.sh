#!/usr/bin/env bash
# Release BreederNear AI: checks, deploy, live smoke test, demo-data reset, and a line in the release log.
# Usage:  PROJECT_ID=breedernear-ai-2026 scripts/release.sh
# Final freeze (17 Oct): PROJECT_ID=breedernear-ai-2026 MIN_INSTANCES=1 scripts/release.sh
#   min-instances=1 keeps one server warm so judges never wait for a cold start (rule R17).
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PROJECT_ID:?Set PROJECT_ID, e.g. PROJECT_ID=breedernear-ai-2026}"
export MIN_INSTANCES="${MIN_INSTANCES:-0}"
REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-breedernear}"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Commit or stash your changes first: a release must match a commit."; exit 1
fi
SHA="$(git rev-parse --short HEAD)"

echo "== 1/5 lint and unit tests"
ruff check .
python -m pytest -m "not live" -q -p no:cacheprovider

echo "== 2/5 deploy ($SHA, min-instances=$MIN_INSTANCES)"
scripts/deploy.sh

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
REVISION="$(gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" \
  --format='value(status.latestReadyRevisionName)')"

echo "== 3/5 live smoke test"
SMOKE="$(PYTHONPATH=. python scripts/smoke_test.py "$URL" | tee /dev/stderr | tail -1)"

echo "== 4/5 reset the demo accounts and sample data"
GOOGLE_CLOUD_PROJECT="$PROJECT_ID" PYTHONPATH=. python scripts/seed_firestore.py

echo "== 5/5 record"
LOG=docs/submission/03-release-log.md
echo "| $(date '+%Y-%m-%d %H:%M %Z') | \`$SHA\` | \`$REVISION\` | $MIN_INSTANCES | $SMOKE |" >> "$LOG"
echo "Released $REVISION ($SHA). Logged in $LOG; commit that file."
