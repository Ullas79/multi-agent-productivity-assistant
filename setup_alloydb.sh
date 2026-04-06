#!/bin/bash
# =============================================================================
# infra/setup_alloydb.sh
# Provisions an AlloyDB cluster + primary instance for AgentFlow.
# Safe to re-run (idempotent).
# Usage: bash infra/setup_alloydb.sh
# =============================================================================

set -euo pipefail
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${BLUE}[AlloyDB]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()     { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${REGION:-us-central1}"
CLUSTER="${ALLOYDB_CLUSTER:-agentflow-cluster}"
INSTANCE="${ALLOYDB_INSTANCE:-agentflow-primary}"
DB_USER="${DB_USER:-agentflow}"
DB_NAME="${DB_NAME:-agentflow}"
DB_PASS="${DB_PASSWORD:-$(openssl rand -base64 20)}"

[ -z "$PROJECT_ID" ] && err "Set GOOGLE_CLOUD_PROJECT"

info "Project: $PROJECT_ID | Region: $REGION"
info "Cluster: $CLUSTER  | Instance: $INSTANCE"

# ── Enable required APIs ──────────────────────────────────────────────────────
info "Enabling AlloyDB & Service Networking APIs..."
gcloud services enable alloydb.googleapis.com servicenetworking.googleapis.com \
    --project="$PROJECT_ID" --quiet
success "APIs enabled"

# ── VPC peering for private connectivity ──────────────────────────────────────
info "Configuring VPC peering for AlloyDB private IP..."
gcloud compute addresses create google-managed-services-default \
    --global --purpose=VPC_PEERING --prefix-length=16 \
    --network=default --project="$PROJECT_ID" 2>/dev/null \
    || warn "VPC peering range already exists – skipping"

gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=google-managed-services-default \
    --network=default --project="$PROJECT_ID" 2>/dev/null \
    || warn "VPC peering already configured"

success "VPC peering ready"

# ── Create AlloyDB cluster ─────────────────────────────────────────────────────
if gcloud alloydb clusters describe "$CLUSTER" \
       --region="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
    warn "Cluster '$CLUSTER' already exists – skipping creation"
else
    info "Creating AlloyDB cluster (this takes ~5 minutes)..."
    gcloud alloydb clusters create "$CLUSTER" \
        --region="$REGION" \
        --password="$DB_PASS" \
        --network=default \
        --project="$PROJECT_ID" --quiet
    success "Cluster created"
fi

# ── Create primary instance ───────────────────────────────────────────────────
if gcloud alloydb instances describe "$INSTANCE" \
       --cluster="$CLUSTER" --region="$REGION" \
       --project="$PROJECT_ID" >/dev/null 2>&1; then
    warn "Instance '$INSTANCE' already exists – skipping"
else
    info "Creating primary instance (CPU=2, ~3 minutes)..."
    gcloud alloydb instances create "$INSTANCE" \
        --cluster="$CLUSTER" \
        --region="$REGION" \
        --instance-type=PRIMARY \
        --cpu-count=2 \
        --project="$PROJECT_ID" --quiet
    success "Instance created"
fi

# ── Get connection info ───────────────────────────────────────────────────────
PRIVATE_IP=$(gcloud alloydb instances describe "$INSTANCE" \
    --cluster="$CLUSTER" --region="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(ipAddress)' 2>/dev/null || echo "pending")

INSTANCE_URI="projects/${PROJECT_ID}/locations/${REGION}/clusters/${CLUSTER}/instances/${INSTANCE}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         AlloyDB Provisioned Successfully!        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Private IP:      ${PRIVATE_IP}"
echo -e "  Instance URI:    ${INSTANCE_URI}"
echo -e "  DB User:         ${DB_USER}"
echo -e "  DB Name:         ${DB_NAME}"
echo ""
echo -e "  Add to .env:"
echo -e "  ALLOYDB_INSTANCE_URI=${INSTANCE_URI}"
echo -e "  DB_HOST=${PRIVATE_IP}"
echo -e "  DB_PASSWORD=${DB_PASS}"
echo ""

# Store in Secret Manager
info "Storing DB password in Secret Manager..."
echo -n "$DB_PASS" | gcloud secrets create agentflow-db-password \
    --data-file=- --project="$PROJECT_ID" 2>/dev/null \
    || echo -n "$DB_PASS" | gcloud secrets versions add agentflow-db-password \
    --data-file=- --project="$PROJECT_ID"
success "Secret stored: agentflow-db-password"
