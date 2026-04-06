# ============================================================
# AgentFlow – Makefile
# Usage: make <target>
# ============================================================

.PHONY: help install dev test lint docker-up docker-down build push deploy clean seed

# Detect OS for open command
UNAME := $(shell uname)
OPEN := $(if $(filter Darwin,$(UNAME)),open,xdg-open)

PROJECT_ID   ?= $(shell gcloud config get-value project 2>/dev/null)
REGION       ?= us-central1
SERVICE_NAME  = agentflow
AR_REPO       = agentflow-repo
IMAGE         = $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(AR_REPO)/$(SERVICE_NAME)

# ── Help ──────────────────────────────────────────
help:
	@echo ""
	@echo "  ⚡ AgentFlow – Available Commands"
	@echo "  =================================="
	@echo "  make install      Install Python dependencies"
	@echo "  make dev          Start local dev server (SQLite, hot reload)"
	@echo "  make test         Run test suite"
	@echo "  make lint         Run flake8 linter"
	@echo "  make docker-up    Start local Postgres + backend via Docker"
	@echo "  make docker-down  Stop Docker services"
	@echo "  make seed         Insert sample data into local DB"
	@echo "  make build        Build Docker image"
	@echo "  make push         Push image to Artifact Registry"
	@echo "  make deploy       Full Cloud Run deploy"
	@echo "  make logs         Tail Cloud Run logs"
	@echo "  make url          Print live service URL"
	@echo "  make clean        Remove caches and temp files"
	@echo ""

# ── Local dev ─────────────────────────────────────
install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -r requirements-test.txt
	@echo "✅ Dependencies installed. Activate with: source .venv/bin/activate"

dev:
	@if [ ! -f .env ]; then cp .env.example .env; echo "⚠️  Created .env with SQLite defaults"; fi
	USE_SQLITE=true \
	uvicorn backend.main:app --reload --port 8080 --host 0.0.0.0

# ── Testing ───────────────────────────────────────
test:
	PYTHONPATH=$(PWD) pytest test_*.py -v --tb=short

test-cov:
	PYTHONPATH=$(PWD) pytest test_*.py -v --cov=backend --cov-report=html --cov-report=term
	$(OPEN) htmlcov/index.html 2>/dev/null || true

lint:
	flake8 backend/ --max-line-length=120 --ignore=E501,W503 \
	  --exclude=__pycache__,.venv,build,dist

# ── Docker ────────────────────────────────────────
docker-up:
	docker compose up -d
	@echo "✅ Services running. Open: http://localhost:8080"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f backend

# ── Seed data ─────────────────────────────────────
seed:
	USE_SQLITE=true python seed_data.py

# ── Cloud Build / Deploy ──────────────────────────
build:
	docker build -t $(IMAGE):latest .
	@echo "✅ Image built: $(IMAGE):latest"

push: build
	gcloud auth configure-docker $(REGION)-docker.pkg.dev --quiet
	docker push $(IMAGE):latest
	@echo "✅ Image pushed"

deploy:
	chmod +x deploy.sh && ./deploy.sh

# ── Cloud Run ops ─────────────────────────────────
logs:
	gcloud run services logs tail $(SERVICE_NAME) --region=$(REGION) --project=$(PROJECT_ID)

url:
	@gcloud run services describe $(SERVICE_NAME) \
	  --region=$(REGION) --project=$(PROJECT_ID) \
	  --format='value(status.url)'

# ── Cleanup ───────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage dist build *.egg-info agentflow.db
	@echo "✅ Cleaned"
