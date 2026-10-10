#!/usr/bin/env bash
# Run the live agent evals N times (default 3) for a repeatability figure; see evals/RESULTS.md.
# Needs Google Cloud credentials: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION=global, GOOGLE_GENAI_USE_VERTEXAI=True.
set -uo pipefail
runs="${1:-3}"
cd "$(dirname "$0")/.."
for i in $(seq 1 "$runs"); do
  echo "== eval run $i of $runs"
  PYTHONPATH=. python -m pytest -m live tests/evals -q -p no:cacheprovider || true
done
sed -n '3p' evals/RESULTS.md
