#!/bin/bash
# =============================================================================
# deploy.sh – Build and deploy AgentFlow to Cloud Run
# =============================================================================

set -euo pipefail
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

# ── Get project info ──────────────────────────────────────────────────────────
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="agentflow"
AR_REPO="agentflow-repo"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}"

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}  ❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID${NC}"
    exit 1
fi

echo -e "${CYAN}  Deploying AgentFlow to Cloud Run...${NC}"
echo -e "  Project:  ${PROJECT_ID}"
echo -e "  Region:   ${REGION}"
echo -e "  Image:    ${IMAGE}"
echo ""

# ── Enable required APIs ─────────────────────────────────────────────────────
echo -e "${CYAN}  [1/5] Enabling APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    alloydb.googleapis.com \
    aiplatform.googleapis.com \
    --project="$PROJECT_ID" --quiet

# ── Create Artifact Registry repo (if not exists) ────────────────────────────
echo -e "${CYAN}  [2/5] Setting up Artifact Registry...${NC}"
gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT_ID" 2>/dev/null || true
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ── Build & push Docker image ────────────────────────────────────────────────
echo -e "${CYAN}  [3/5] Building Docker image...${NC}"
docker build -t "${IMAGE}:latest" .

echo -e "${CYAN}  [4/5] Pushing image...${NC}"
docker push "${IMAGE}:latest"

# ── Deploy to Cloud Run ──────────────────────────────────────────────────────
echo -e "${CYAN}  [5/5] Deploying to Cloud Run...${NC}"
gcloud run deploy "$SERVICE_NAME" \
    --image="${IMAGE}:latest" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --cpu=2 \
    --memory=2Gi \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},PYTHONUNBUFFERED=1" \
    --quiet

# ── Print URL ─────────────────────────────────────────────────────────────────
URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" --project="$PROJECT_ID" \
    --format='value(status.url)')

echo ""
echo -e "${GREEN}  ✅ Deployed successfully!${NC}"
echo -e "${GREEN}  🌐 URL: ${URL}${NC}"
echo -e "  📖 API docs: ${URL}/docs"
echo -e "  💬 Chat UI:  ${URL}/"
