#!/bin/bash
# =============================================================================
# cloudshell_start.sh
# Run this FIRST in Google Cloud Shell after opening the repo:
#   bash cloudshell_start.sh
#
# It sets gcloud project, checks prerequisites, then calls deploy.sh
# =============================================================================

set -euo pipefail
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${CYAN}"
cat << 'EOF'
 ___  ___  ___  ________   ___________  ________ ___       ________  ___       __
|\  \|\  \|\  \|\   ___  \|\___   ___\\   __  \|\  \     |\   __  \|\  \     |\  \
\ \  \\\  \ \  \ \  \\ \  \|___ \  \_\ \  \|\  \ \  \    \ \  \|\  \ \  \    \ \  \
 \ \   __  \ \  \ \  \\ \  \   \ \  \ \ \  \\\  \ \  \    \ \  \\\  \ \  \  __\ \  \
  \ \  \ \  \ \  \ \  \\ \  \   \ \  \ \ \  \\\  \ \  \____\ \  \\\  \ \  \|\__\_\  \
   \ \__\ \__\ \__\ \__\\ \__\   \ \__\ \ \_______\ \_______\ \_______\ \____________\
    \|__|\|__|\|__|\|__| \|__|    \|__|  \|_______|\|_______|\|_______|\|____________|
EOF
echo -e "${NC}"
echo -e "${GREEN}  Gen AI Academy APAC · Cohort 1 Hackathon${NC}"
echo ""

# ── Verify gcloud is configured ───────────────────────────────────────────────
PROJECT=$(gcloud config get-value project 2>/dev/null || true)
if [ -z "$PROJECT" ]; then
    read -p "Enter your GCP Project ID: " PROJECT
    gcloud config set project "$PROJECT"
    echo ""
fi
echo -e "  ${CYAN}Project:${NC} $PROJECT"

# ── Check billing is enabled ──────────────────────────────────────────────────
BILLING=$(gcloud beta billing projects describe "$PROJECT" \
    --format='value(billingEnabled)' 2>/dev/null || echo "false")
if [ "$BILLING" != "True" ]; then
    echo -e "${YELLOW}  ⚠️  Billing does not appear to be enabled for project $PROJECT.${NC}"
    echo "     Enable billing at: https://console.cloud.google.com/billing"
    read -p "  Continue anyway? (y/N): " CONT
    [ "${CONT:-n}" != "y" ] && exit 1
fi

# ── Setup Vertex AI ───────────────────────────────────────────────────────────
echo -e "${CYAN}  Setting up Vertex AI...${NC}"
gcloud services enable aiplatform.googleapis.com
echo -e "${GREEN}  Vertex AI API enabled.${NC}"

# We don't need a GOOGLE_API_KEY anymore. The deploy script will use the Cloud Run
# default service account, which we'll grant permissions to during deployment.
export GOOGLE_CLOUD_PROJECT="$PROJECT"

# ── Run the main deploy script ────────────────────────────────────────────────
echo ""
chmod +x deploy.sh
./deploy.sh
