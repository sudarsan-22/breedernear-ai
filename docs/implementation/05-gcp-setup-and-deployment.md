# Google Cloud Setup and Deployment

Run these steps once. Replace `PROJECT_ID`. Commands are for Linux/macOS bash.

## 0. Prerequisites (local machine)

```bash
# Python tooling: Ubuntu's python3 ships without pip/venv
sudo apt install -y python3-pip python3-venv

# Google Cloud CLI: https://cloud.google.com/sdk/docs/install
gcloud --version
```

## 1. Project and billing

```bash
export PROJECT_ID=breedernear-ai-2026          # must be globally unique
export REGION=asia-south1

gcloud auth login
gcloud projects create $PROJECT_ID --name="BreederNear AI"
gcloud config set project $PROJECT_ID
# Link billing (free trial or hackathon credits) in the console:
#   https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID
gcloud auth application-default login
gcloud auth application-default set-quota-project $PROJECT_ID
```

**Check the credit expiry date.** The app must stay up until at least 7 Nov, and until 4 Dec if shortlisted.

## 2. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com
```

## 3. Firestore and Cloud Storage

```bash
gcloud firestore databases create --location=$REGION --type=firestore-native

export BUCKET=${PROJECT_ID}-breedernear-uploads
gcloud storage buckets create gs://$BUCKET --location=$REGION --uniform-bucket-level-access

cat > /tmp/lifecycle.json <<'EOF'
{"rule":[{"action":{"type":"Delete"},"condition":{"age":30}}]}
EOF
gcloud storage buckets update gs://$BUCKET --lifecycle-file=/tmp/lifecycle.json
```

## 4. Service account (least privilege)

```bash
export SA=breedernear-run@${PROJECT_ID}.iam.gserviceaccount.com
gcloud iam service-accounts create breedernear-run --display-name="BreederNear Cloud Run"

for ROLE in roles/aiplatform.user roles/datastore.user roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA" --role=$ROLE
done

gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member="serviceAccount:$SA" --role=roles/storage.objectAdmin
```

No service-account key files. Cloud Run uses the attached service account, and local dev uses your own ADC.

## 5. Budget alert

Console → Billing → Budgets & alerts → create a budget for this project (e.g. ₹2,000 or the credit amount), with alerts at 50%, 90% and 100% sent to both team members.

## 6. Environment variables

`.env.example` (committed). The real `.env` is never committed.

```bash
# Gemini via Google Cloud (used on Cloud Run and recommended locally)
GOOGLE_CLOUD_PROJECT=breedernear-ai-2026
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_ENTERPRISE=True      # current ADK docs; older ADK versions read GOOGLE_GENAI_USE_VERTEXAI=True
# Alternative for local dev only: AI Studio key
# GOOGLE_API_KEY=...

BREEDERNEAR_MODEL=gemini-3.8-flash       # re-check the newest GA Flash ID on build day; never gemini-2.x
BREEDERNEAR_BUCKET=breedernear-ai-2026-breedernear-uploads
BREEDERNEAR_REGION=asia-south1
RATE_LIMIT_PER_HOUR=30
MAX_UPLOAD_MB=5
```

Check which variable your installed ADK version reads (`GOOGLE_GENAI_USE_ENTERPRISE` or `GOOGLE_GENAI_USE_VERTEXAI`). Setting both to `True` is harmless.

## 7. Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then edit

python scripts/seed_firestore.py            # seed breeders, listings, products, reference data, simulated registry

adk web agents                              # ADK dev UI: test agents and tools in isolation
uvicorn app.main:app --reload --port 8080   # full app: http://localhost:8080
pytest                                      # unit tests
adk eval agents/breedernear evals/core.evalset.json --config_file_path=evals/test_config.json
```

## 8. Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
COPY . .
USER appuser
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
```

Add a `.dockerignore` excluding `.venv`, `.git`, `docs/`, `tests/`, `.env*` and `data/samples/`.

## 9. Deploy to Cloud Run

```bash
gcloud run deploy breedernear \
  --source . \
  --region $REGION \
  --service-account $SA \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 1 \
  --session-affinity \
  --memory 1Gi --cpu 1 \
  --timeout 300 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_ENTERPRISE=True,GOOGLE_GENAI_USE_VERTEXAI=True,BREEDERNEAR_MODEL=gemini-3.8-flash,BREEDERNEAR_BUCKET=$BUCKET,BREEDERNEAR_REGION=$REGION"
```

- `--max-instances 1` is used **because ADK sessions are in-memory in the MVP**: a second instance wouldn't know the chat. Raise it after moving to a persistent session service (see [01-architecture.md](01-architecture.md#key-decisions)).
- `--min-instances 1` means no cold start for judges. A small always-on cost; keep it from 17 Oct until results.
- If `--allow-unauthenticated` fails because of an organisation policy, use a personal-account project (no organisation) or ask the org admin.
- `scripts/deploy.sh` wraps this command and prints the URL and revision name.

### Rollback

```bash
gcloud run revisions list --service breedernear --region $REGION
gcloud run services update-traffic breedernear --region $REGION --to-revisions=<GOOD_REVISION>=100
```

Write the known-good revision name into the [submission checklist](../event/04-submission-checklist.md) at submission time.

### Logs

```bash
gcloud run services logs read breedernear --region $REGION --limit 100
```

## 10. Deploy early, deploy often

- **Day 1:** deploy a "hello" version that answers one Gemini call. That proves billing, APIs, IAM and the model ID all work.
- After every feature merges: redeploy and run `scripts/smoke_test.py <URL>`.
- From 17 Oct: deploy only fixes, and only after the smoke test passes locally.
