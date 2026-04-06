#!/bin/bash
# =============================================================================
# run_local.sh – Start AgentFlow locally in Cloud Shell (no PostgreSQL needed)
#
# Usage:
#   bash run_local.sh
# =============================================================================

set -euo pipefail
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════╗"
echo "  ║   AgentFlow – Local Dev Server    ║"
echo "  ╚═══════════════════════════════════╝"
echo -e "${NC}"

# ── Create .env from template if missing ──────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}  ✅ Created .env from .env.example (SQLite mode)${NC}"
fi

# ── Set GCP project for Vertex AI (optional) ─────────────────────────────────
PROJECT=$(gcloud config get-value project 2>/dev/null || true)
if [ -n "$PROJECT" ]; then
    export GOOGLE_CLOUD_PROJECT="$PROJECT"
    echo -e "  ☁️  GCP Project: ${PROJECT}"
else
    echo -e "${YELLOW}  ⚠️  No GCP project set – Vertex AI chat will use fallback mode${NC}"
fi

# ── Install dependencies ─────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo -e "${CYAN}  📦 Setting up virtual environment...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    echo -e "${GREEN}  ✅ Dependencies installed${NC}"
else
    source .venv/bin/activate
    echo -e "  ✅ Virtual environment activated"
fi

# ── Start the server ─────────────────────────────────────────────────────────
export USE_SQLITE=true
echo ""
echo -e "${GREEN}  🚀 Starting AgentFlow on port 8080...${NC}"
echo -e "  📖 API docs: http://localhost:8080/docs"
echo -e "  💬 Chat UI:  http://localhost:8080/"
echo ""

uvicorn backend.main:app --reload --port 8080 --host 0.0.0.0
