#!/usr/bin/env python3
"""
scripts/seed_data.py
Populates the database with realistic demo data for presentations.

Usage:
    python scripts/seed_data.py
    # or via Makefile:
    make seed
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.database.connection import init_db, AsyncSessionLocal
from backend.database import crud


TASKS = [
    {
        "title": "Prepare Q2 Business Review presentation",
        "description": "Compile metrics, create slides, and rehearse for the executive team",
        "priority": "high",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "tags": ["presentation", "executive", "q2"],
    },
    {
        "title": "Review pull requests for authentication module",
        "description": "3 PRs waiting: JWT refresh logic, MFA setup, and session management",
        "priority": "high",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "tags": ["code-review", "security"],
    },
    {
        "title": "Update API documentation",
        "description": "Add new endpoints introduced in v1.2 to the developer docs",
        "priority": "medium",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        "tags": ["docs", "api"],
    },
    {
        "title": "Interview candidate for Senior ML Engineer role",
        "description": "Technical interview + system design round. Candidate: Priya Sharma",
        "priority": "high",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "tags": ["hiring", "ml"],
    },
    {
        "title": "Set up monitoring alerts for production",
        "description": "Configure Cloud Monitoring dashboards and PagerDuty alerts",
        "priority": "medium",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "tags": ["devops", "monitoring"],
    },
    {
        "title": "Plan team offsite – Q3",
        "description": "Book venue, arrange travel, create agenda for 2-day offsite",
        "priority": "low",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "tags": ["team", "planning"],
    },
    {
        "title": "Refactor data pipeline for AlloyDB",
        "description": "Migrate ETL jobs from BigQuery to AlloyDB for lower latency",
        "priority": "medium",
        "tags": ["engineering", "database", "alloydb"],
    },
    {
        "title": "Write blog post: Multi-Agent AI with ADK",
        "description": "Document the architecture and lessons learned from the hackathon project",
        "priority": "low",
        "tags": ["writing", "ai", "adk"],
    },
]

EVENTS = [
    {
        "title": "Daily Standup",
        "description": "Team sync – blockers, progress, priorities",
        "start_time": (datetime.now(timezone.utc).replace(hour=9, minute=0, second=0) + timedelta(days=1)).isoformat(),
        "end_time": (datetime.now(timezone.utc).replace(hour=9, minute=30, second=0) + timedelta(days=1)).isoformat(),
        "location": "Google Meet",
        "attendees": ["alice@company.com", "bob@company.com", "carol@company.com"],
    },
    {
        "title": "Q2 Business Review",
        "description": "Quarterly review with leadership team – KPIs, OKRs, roadmap",
        "start_time": (datetime.now(timezone.utc).replace(hour=14, minute=0, second=0) + timedelta(days=2)).isoformat(),
        "end_time": (datetime.now(timezone.utc).replace(hour=16, minute=0, second=0) + timedelta(days=2)).isoformat(),
        "location": "Boardroom A",
        "attendees": ["ceo@company.com", "cto@company.com", "vp-product@company.com"],
    },
    {
        "title": "1:1 with Engineering Manager",
        "description": "Weekly check-in: career growth, feedback, blockers",
        "start_time": (datetime.now(timezone.utc).replace(hour=11, minute=0, second=0) + timedelta(days=3)).isoformat(),
        "end_time": (datetime.now(timezone.utc).replace(hour=11, minute=30, second=0) + timedelta(days=3)).isoformat(),
        "location": "Zoom",
        "attendees": ["manager@company.com"],
    },
    {
        "title": "ML Engineer Interview – Priya Sharma",
        "description": "Technical round: system design + ML fundamentals",
        "start_time": (datetime.now(timezone.utc).replace(hour=15, minute=0, second=0) + timedelta(days=3)).isoformat(),
        "end_time": (datetime.now(timezone.utc).replace(hour=16, minute=30, second=0) + timedelta(days=3)).isoformat(),
        "location": "Interview Room 2",
        "attendees": ["hr@company.com", "tech-lead@company.com"],
    },
    {
        "title": "Product Roadmap Planning",
        "description": "H2 roadmap prioritisation with product and engineering",
        "start_time": (datetime.now(timezone.utc).replace(hour=10, minute=0, second=0) + timedelta(days=5)).isoformat(),
        "end_time": (datetime.now(timezone.utc).replace(hour=12, minute=0, second=0) + timedelta(days=5)).isoformat(),
        "location": "Conference Room B",
        "attendees": ["pm@company.com", "design@company.com", "eng-lead@company.com"],
    },
    {
        "title": "AgentFlow Demo – Hackathon Presentation",
        "description": "Live demo of the multi-agent AI system to judges and peers",
        "start_time": (datetime.now(timezone.utc).replace(hour=13, minute=0, second=0) + timedelta(days=7)).isoformat(),
        "end_time": (datetime.now(timezone.utc).replace(hour=14, minute=0, second=0) + timedelta(days=7)).isoformat(),
        "location": "Main Stage",
        "attendees": ["judge1@hackathon.com", "judge2@hackathon.com"],
    },
]

NOTES = [
    {
        "title": "AgentFlow Architecture Notes",
        "content": """# AgentFlow Architecture

## Overview
Multi-agent AI system built with Google ADK and Gemini 2.0 Flash.

## Agent Hierarchy
- **Orchestrator** – routes intent to sub-agents
- **Task Agent** – manages tasks via MCP tools
- **Calendar Agent** – schedules events, checks availability
- **Notes Agent** – knowledge management
- **Research Agent** – answers questions

## Tech Stack
- Backend: FastAPI + Python 3.11
- AI: Gemini 2.0 Flash via Google ADK
- Tools: MCP (Model Context Protocol)
- DB: AlloyDB (PostgreSQL-compatible)
- Deploy: Cloud Run + Artifact Registry

## Key Design Decisions
1. SSE streaming for real-time AI responses
2. Sub-agents each have their own MCP server for tool isolation
3. Session memory stored in AlloyDB for context persistence
""",
        "tags": ["architecture", "agentflow", "hackathon"],
        "is_pinned": True,
    },
    {
        "title": "Gen AI Academy – Key Learnings",
        "content": """# Gen AI Academy APAC Cohort 1 – Key Learnings

## Module 1: Gemini API
- Use `gemini-2.0-flash` for speed + cost efficiency
- Streaming via SSE dramatically improves UX
- System instructions shape agent personality and behaviour

## Module 2: Google ADK
- LlmAgent is the core building block
- Sub-agents enable specialisation and parallel workloads
- InMemorySessionService for dev; swap for DB-backed in prod

## Module 3: MCP
- Model Context Protocol standardises tool integration
- stdio transport works well for local subprocesses
- Each MCP server should have a focused tool set

## Module 4: AlloyDB
- PostgreSQL-compatible → standard SQLAlchemy works
- AlloyDB Connector handles Cloud Run auth transparently
- pgvector extension available for semantic search

## Next Steps
- Add vector search to notes for semantic retrieval
- Implement agent-to-agent memory sharing
- Add Google Calendar / Workspace integration
""",
        "tags": ["learning", "genai", "academy", "adk"],
        "is_pinned": True,
    },
    {
        "title": "Q3 Project Ideas",
        "content": """# Q3 Project Ideas Backlog

1. **AI Code Reviewer** – Agent that reviews PRs and suggests improvements
2. **Meeting Summariser** – Transcribe + summarise + create action items
3. **Customer Support Bot** – Multi-agent with escalation to human
4. **Data Pipeline Monitor** – Agent watches ETL jobs, alerts on anomalies
5. **Competitive Intelligence** – Research agent scrapes and summarises competitor updates

## Evaluation Criteria
- Business impact (High/Medium/Low)
- Technical complexity (1-5)
- Time to MVP (weeks)

| Project | Impact | Complexity | Weeks |
|---|---|---|---|
| Code Reviewer | High | 3 | 4 |
| Meeting Summariser | High | 2 | 3 |
| Support Bot | High | 4 | 8 |
| Pipeline Monitor | Medium | 3 | 3 |
| Competitive Intel | Medium | 4 | 6 |
""",
        "tags": ["ideas", "q3", "planning"],
        "is_pinned": False,
    },
    {
        "title": "Cloud Run Deployment Checklist",
        "content": """# Cloud Run Deployment Checklist

## Before Deploying
- [ ] Set GOOGLE_API_KEY in Secret Manager
- [ ] AlloyDB cluster running and accessible
- [ ] Docker image builds successfully locally
- [ ] All tests passing (pytest tests/ -v)
- [ ] Environment variables documented

## gcloud Commands
```bash
# Enable APIs
gcloud services enable run.googleapis.com alloydb.googleapis.com

# Build and push
docker build -t us-central1-docker.pkg.dev/PROJECT/agentflow-repo/agentflow:latest .
docker push us-central1-docker.pkg.dev/PROJECT/agentflow-repo/agentflow:latest

# Deploy
gcloud run deploy agentflow --region=us-central1 --allow-unauthenticated
```

## Post-Deploy Checks
- [ ] /api/health returns 200
- [ ] Chat endpoint works end-to-end
- [ ] Database tables created (check startup logs)
- [ ] SSE streaming works in browser
""",
        "tags": ["devops", "cloud-run", "deployment", "checklist"],
        "is_pinned": False,
    },
    {
        "title": "Meeting Notes – Sprint Planning",
        "content": """# Sprint Planning – Sprint 42

**Date:** Today  
**Attendees:** Alice, Bob, Carol, Dave

## Sprint Goal
Ship AgentFlow v1.0 with full multi-agent support and production deploy.

## Committed Stories
1. ✅ Orchestrator agent routing (5 pts)
2. ✅ Task MCP server (3 pts)
3. ✅ Calendar MCP server (3 pts)
4. ✅ Notes MCP server (3 pts)
5. 🔄 Frontend SPA (5 pts)
6. 🔄 Cloud Run deployment (3 pts)
7. ❌ Semantic search (deferred to next sprint)

## Action Items
- Alice: Finalize frontend design by Wednesday
- Bob: Set up AlloyDB in staging env
- Carol: Write test suite for all API endpoints
- Dave: Record demo video

## Blockers
- AlloyDB quota limit – request increase filed (ticket #4521)
""",
        "tags": ["meeting", "sprint", "planning"],
        "is_pinned": False,
    },
]


async def seed():
    print("🌱 Seeding AgentFlow database...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Tasks
        print(f"  Creating {len(TASKS)} tasks...")
        for i, t in enumerate(TASKS):
            task = await crud.create_task(db, **t)
            # Mark some as in_progress / done
            if i == 0:
                await crud.update_task(db, str(task.id), status="in_progress")
            elif i in (1, 2):
                await crud.update_task(db, str(task.id), status="done")
        await db.commit()

        # Events
        print(f"  Creating {len(EVENTS)} calendar events...")
        for e in EVENTS:
            await crud.create_event(db, **e)
        await db.commit()

        # Notes
        print(f"  Creating {len(NOTES)} notes...")
        for n in NOTES:
            await crud.create_note(db, **n)
        await db.commit()

    print(f"✅ Seeded: {len(TASKS)} tasks · {len(EVENTS)} events · {len(NOTES)} notes")
    print("   Open http://localhost:8080 to see your data!")


if __name__ == "__main__":
    asyncio.run(seed())
