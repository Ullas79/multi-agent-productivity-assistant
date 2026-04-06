# ⚡ AgentFlow – Multi-Agent AI Productivity Hub

> **Gen AI Academy APAC Cohort 1 Hackathon Submission**  
> Built with **Gemini 2.0 Flash · Google ADK · Cloud Run · AlloyDB · MCP**

[![Deploy to Cloud Run](https://img.shields.io/badge/Deploy-Cloud%20Run-blue?logo=google-cloud)](https://cloud.google.com/run)
[![Python 3.11](https://img.shields.io/badge/Python-3.11+-green?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)

---

## 🎯 What is AgentFlow?

AgentFlow is a **multi-agent AI system** that helps users manage tasks, schedules, and information through natural language. A primary **Orchestrator Agent** (Gemini 2.0 Flash) coordinates four specialised sub-agents, each connected to real-world data via **MCP (Model Context Protocol)** tools backed by **AlloyDB**.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User (Browser)                           │
│              React SPA · Chat · Tasks · Calendar · Notes        │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / SSE / WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend (Cloud Run)                     │
│              /api/chat  /api/tasks  /api/events  /api/notes     │
└────────────────────────────┬────────────────────────────────────┘
                             │ Google ADK
┌────────────────────────────▼────────────────────────────────────┐
│              🤖 Orchestrator Agent (Gemini 2.0 Flash)           │
│        Routes intent → coordinates sub-agents → synthesises     │
└──────┬──────────────┬──────────────┬────────────────┬──────────┘
       │ ADK          │ ADK          │ ADK            │ ADK
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼──────┐  ┌─────▼──────┐
│   Task      │ │  Calendar  │ │   Notes   │  │  Research  │
│   Agent     │ │   Agent    │ │   Agent   │  │   Agent    │
│  (Gemini)   │ │  (Gemini)  │ │  (Gemini) │  │  (Gemini)  │
└──────┬──────┘ └─────┬──────┘ └────┬──────┘  └────────────┘
       │ MCP          │ MCP         │ MCP
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼──────┐
│  Task MCP   │ │Calendar MCP│ │ Notes MCP │
│  Server     │ │  Server    │ │  Server   │
└──────┬──────┘ └─────┬──────┘ └────┬──────┘
       └──────────────┴──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    AlloyDB (PostgreSQL)     │
        │  tasks · events · notes     │
        │      agent_memory           │
        └─────────────────────────────┘
```

### Key Components

| Layer | Technology | Purpose |
|---|---|---|
| **LLM** | Gemini 2.0 Flash | Natural language understanding & generation |
| **Agent Framework** | Google ADK 1.2 | Agent lifecycle, tool routing, multi-agent coordination |
| **Tool Protocol** | MCP (stdio) | Standardised agent-to-tool communication |
| **API** | FastAPI | REST API + SSE streaming + WebSocket |
| **Database** | AlloyDB (PostgreSQL) | Structured data storage with async ORM |
| **Deployment** | Cloud Run | Serverless, auto-scaling, zero cold-start config |
| **CI/CD** | GitHub Actions | Automated build & deploy pipeline |

---

## 📁 Project Structure

```
agentflow/
├── backend/
│   ├── main.py               # FastAPI app, all routes, SSE/WS
│   ├── config.py             # Settings from env vars
│   ├── agents/
│   │   ├── orchestrator.py   # Primary agent (coordinates all sub-agents)
│   │   └── sub_agents.py     # Task, Calendar, Notes, Research agents
│   ├── mcp_servers/
│   │   ├── task_server.py    # MCP: task CRUD tools
│   │   ├── calendar_server.py# MCP: calendar event tools
│   │   └── notes_server.py   # MCP: notes + search tools
│   ├── database/
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── connection.py     # AlloyDB async engine
│   │   └── crud.py           # DB operations
│   └── requirements.txt
├── frontend/
│   └── index.html            # Single-page app (Tailwind CSS, Vanilla JS)
├── tests/
│   └── test_api.py           # Pytest async test suite
├── .github/workflows/
│   └── deploy.yml            # GitHub Actions CI/CD
├── Dockerfile                # Multi-stage build
├── docker-compose.yml        # Local dev (Postgres + backend)
├── cloudbuild.yaml           # Cloud Build config
├── deploy.sh                 # One-shot Cloud Shell deploy
└── setup_local.sh            # Local dev setup
```

---

## 🚀 Quick Start

### Option A: Local Development (5 minutes)

**Prerequisites:** Python 3.11+, Docker, a [Google AI API Key](https://aistudio.google.com/app/apikey)

```bash
# 1. Clone repo
git clone https://github.com/YOUR_USERNAME/agentflow.git
cd agentflow

# 2. Run setup (creates venv, starts Postgres, installs deps)
chmod +x setup_local.sh && ./setup_local.sh

# 3. Set API key in .env
echo "GOOGLE_API_KEY=your_key_here" >> .env

# 4. Start server
source .venv/bin/activate
export $(cat .env | xargs)
export PYTHONPATH=$(pwd)
uvicorn backend.main:app --reload --port 8080
```

Open **http://localhost:8080** → You're live! 🎉

---

### Option B: Deploy to Cloud Run (via Cloud Shell)

```bash
# In Google Cloud Shell
git clone https://github.com/YOUR_USERNAME/agentflow.git
cd agentflow

# One-command deploy (handles AlloyDB, Artifact Registry, secrets, Cloud Run)
chmod +x deploy.sh && ./deploy.sh
```

The script will:
1. Enable all required GCP APIs
2. Create Artifact Registry repository
3. Store secrets in Secret Manager
4. Provision AlloyDB cluster + primary instance
5. Build & push Docker image
6. Deploy to Cloud Run with full configuration

---

### Option C: Cloud Build CI/CD

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_SERVICE_NAME=agentflow
```

---

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | ✅ | - | Gemini API key from AI Studio |
| `GOOGLE_CLOUD_PROJECT` | Cloud only | - | GCP Project ID |
| `DB_HOST` | ✅ | `localhost` | PostgreSQL/AlloyDB host |
| `DB_PORT` | | `5432` | Database port |
| `DB_USER` | | `agentflow` | Database user |
| `DB_PASSWORD` | ✅ | - | Database password |
| `DB_NAME` | | `agentflow` | Database name |
| `ALLOYDB_INSTANCE_URI` | Cloud only | - | AlloyDB connector URI |
| `DEBUG` | | `false` | Enable debug logging |

---

## 🤖 Agent Capabilities

### Orchestrator Agent
Routes user intent across all sub-agents and synthesises responses.

**Example prompts:**
- *"Create a high-priority task to review the Q2 report, due Friday, then schedule 2 hours on Thursday to work on it"*
- *"What's my workload this week? Show tasks and calendar"*
- *"Remember that the client deadline moved to July 15th"*

### Task Manager Agent (MCP Tools)
| Tool | Description |
|---|---|
| `create_task` | Create task with priority, due date, tags |
| `list_tasks` | Filter by status/priority |
| `update_task` | Update any task field |
| `delete_task` | Remove a task |
| `get_task_summary` | Stats: total, by status, overdue |

### Calendar Agent (MCP Tools)
| Tool | Description |
|---|---|
| `create_event` | Schedule event with attendees |
| `list_events` | Filter by date range |
| `get_upcoming_events` | Next N days |
| `check_availability` | Detect scheduling conflicts |
| `update_event` / `delete_event` | Manage events |

### Notes Agent (MCP Tools)
| Tool | Description |
|---|---|
| `create_note` | Save note with tags + pin |
| `list_notes` | Browse/filter notes |
| `search_notes` | Full-text search |
| `get_note` | Retrieve by ID |
| `update_note` / `delete_note` | Manage notes |

### Research Agent
Uses Gemini's built-in knowledge to answer questions, explain concepts, and provide information.

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | SSE streaming chat with orchestrator |
| `WS` | `/ws/chat/{session_id}` | WebSocket chat alternative |
| `GET` | `/api/health` | Health check |
| `CRUD` | `/api/tasks` | Task management |
| `CRUD` | `/api/events` | Calendar events |
| `CRUD` | `/api/notes` | Notes |
| `GET` | `/api/sessions/{id}/history` | Conversation history |
| `GET` | `/docs` | Interactive Swagger UI |

**Interactive API docs:** `https://YOUR_SERVICE_URL/docs`

---

## 🗄️ Database Schema (AlloyDB)

```sql
tasks          -- id, title, description, status, priority, due_date, tags
calendar_events-- id, title, start_time, end_time, location, attendees
notes          -- id, title, content, tags, is_pinned
agent_memory   -- id, session_id, role, content, agent_name
```

---

## 🧪 Running Tests

```bash
# Install test deps
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=backend --cov-report=html
```

---

## 🛠️ Tech Stack

- **Google Gemini 2.0 Flash** – State-of-the-art LLM for all agents
- **Google ADK 1.2** – Agent Development Kit for multi-agent orchestration
- **MCP (Model Context Protocol)** – Tool integration standard
- **AlloyDB** – PostgreSQL-compatible managed database (AI-ready)
- **FastAPI** – Async Python web framework
- **SQLAlchemy 2.0** – Async ORM
- **Cloud Run** – Serverless container platform
- **Artifact Registry** – Container image storage
- **Secret Manager** – Secure credential storage
- **GitHub Actions** – CI/CD pipeline

---

## 📋 Hackathon Checklist

- [x] Multi-agent system (orchestrator + 4 sub-agents)
- [x] AlloyDB (PostgreSQL) for structured data
- [x] MCP integration (3 MCP servers: tasks, calendar, notes)
- [x] Multi-step workflow handling
- [x] FastAPI-based API with SSE streaming + WebSocket
- [x] Production UI (single-page app)
- [x] Cloud Run deployment
- [x] Gemini 2.0 Flash + Google ADK
- [x] GitHub Actions CI/CD
- [x] Comprehensive test suite

---

## 👤 Team

**[Your Name]** – Solo / Team Name  
Gen AI Academy APAC Edition · Cohort 1 · 2025
