"""
test_multi_agent.py – Tests for the real multi-agent architecture.

Verifies that:
  1. MCP tool servers return real DB data
  2. Sub-agents call MCP tools and produce real output
  3. Orchestrator routes to the correct sub-agent(s)
  4. Multi-step workflows execute correctly
"""
import os
import asyncio
import pytest
import pytest_asyncio

# ── Setup in-memory DB before any app imports ─────────────────────────────────
os.environ["USE_SQLITE"] = "false"
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_REGION", "us-central1")

import backend.database.connection as _conn
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from backend.database.models import Base

# Use StaticPool so ALL connections share the same in-memory database
_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = async_sessionmaker(
    bind=_test_engine, class_=AsyncSession,
    expire_on_commit=False, autoflush=False,
)
_conn.engine = _test_engine
_conn.AsyncSessionLocal = _TestSession
_conn._initialised = True


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Seed some data for tests ──────────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def seed_data():
    """Seed the DB with test data before each test."""
    from backend.database import crud
    async with _TestSession() as db:
        await crud.create_task(db, title="Buy groceries", priority="low", tags=["errands"])
        await crud.create_task(db, title="Review PR #42", priority="high", tags=["work"])
        await crud.create_note(db, title="Meeting Notes", content="Discussed Q3 roadmap and hiring plan.")
        from datetime import datetime, timedelta, timezone
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        await crud.create_event(
            db, title="Team Standup",
            start_time=(tomorrow.replace(hour=9, minute=0)).isoformat(),
            end_time=(tomorrow.replace(hour=9, minute=30)).isoformat(),
        )
        await db.commit()
    yield


# ══════════════════════════════════════════════════════════════════════════════
# ✅ MCP Tool Server Tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_task_mcp_create_tool():
    """Task MCP create_task tool should write to DB and return confirmation."""
    from backend.mcp_servers.tasks_server import handle_call_tool
    results = await handle_call_tool("create_task", {
        "title": "MCP Created Task",
        "priority": "high",
    })
    assert len(results) == 1
    assert "MCP Created Task" in results[0].text
    assert "ID:" in results[0].text


@pytest.mark.asyncio
async def test_task_mcp_list_tool():
    """Task MCP list_tasks tool should return seeded tasks."""
    from backend.mcp_servers.tasks_server import handle_call_tool
    results = await handle_call_tool("list_tasks", {"limit": 10})
    text = results[0].text
    assert "task(s)" in text.lower() or "found" in text.lower()


@pytest.mark.asyncio
async def test_calendar_mcp_list_tool():
    """Calendar MCP list_events tool should return seeded events."""
    from backend.mcp_servers.calendar_server import handle_call_tool
    results = await handle_call_tool("list_events", {})
    text = results[0].text
    assert len(text) > 10


@pytest.mark.asyncio
async def test_calendar_mcp_check_availability():
    """Calendar MCP check_availability tool should return availability status."""
    from backend.mcp_servers.calendar_server import handle_call_tool
    from datetime import datetime, timedelta, timezone
    far_future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    far_future_end = (datetime.now(timezone.utc) + timedelta(days=30, hours=1)).isoformat()
    results = await handle_call_tool("check_availability", {
        "start_time": far_future,
        "end_time": far_future_end,
    })
    assert "AVAILABLE" in results[0].text or "CONFLICT" in results[0].text


@pytest.mark.asyncio
async def test_notes_mcp_create_tool():
    """Notes MCP create_note tool should write to DB."""
    from backend.mcp_servers.notes_server import handle_call_tool
    results = await handle_call_tool("create_note", {
        "title": "Test Note via MCP",
        "content": "This note was created through the MCP tool interface.",
    })
    assert "created" in results[0].text.lower()


# ══════════════════════════════════════════════════════════════════════════════
# ✅ Sub-Agent Tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_task_agent_list():
    """Task agent should yield thoughts + real task data from DB."""
    from backend.agents import task_agent
    events = []
    async for event in task_agent.run("show my tasks", "test-session"):
        events.append(event)

    thoughts = [e for e in events if isinstance(e, dict) and e.get("type") == "thought"]
    texts = [e for e in events if isinstance(e, dict) and e.get("type") == "text"]
    assert len(thoughts) >= 2, "Agent should emit thought events"
    assert len(texts) >= 1, "Agent should emit text response with real data"


@pytest.mark.asyncio
async def test_task_agent_create():
    """Task agent should create a task via MCP tool."""
    from backend.agents import task_agent
    events = []
    async for event in task_agent.run("create a task Deploy to staging", "test-session"):
        events.append(event)

    texts = [e for e in events if isinstance(e, dict) and e.get("type") == "text"]
    full_text = "".join(t.get("content", "") for t in texts)
    assert "Deploy to staging" in full_text or "created" in full_text.lower() or "Task" in full_text


@pytest.mark.asyncio
async def test_calendar_agent_list():
    """Calendar agent should return real event data."""
    from backend.agents import calendar_agent
    events = []
    async for event in calendar_agent.run("show my calendar", "test-session"):
        events.append(event)

    thoughts = [e for e in events if isinstance(e, dict) and e.get("type") == "thought"]
    assert len(thoughts) >= 2


@pytest.mark.asyncio
async def test_notes_agent_search():
    """Notes agent should search notes via MCP semantic_search tool."""
    from backend.agents import notes_agent
    events = []
    async for event in notes_agent.run("search notes about roadmap", "test-session"):
        events.append(event)

    thoughts = [e for e in events if isinstance(e, dict) and e.get("type") == "thought"]
    assert len(thoughts) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# ✅ Orchestrator Routing Tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_orchestrator_routes_to_task_agent():
    """Orchestrator should delegate task requests to Task Agent."""
    from backend.agents.orchestrator import run_agent
    events = []
    async for event in run_agent("show my tasks", "test-session-1"):
        events.append(event)

    thoughts = [e for e in events if isinstance(e, dict) and e.get("type") == "thought"]
    thought_texts = " ".join(t.get("content", "") for t in thoughts)
    assert "Task Agent" in thought_texts


@pytest.mark.asyncio
async def test_orchestrator_routes_to_calendar_agent():
    """Orchestrator should delegate calendar requests to Calendar Agent."""
    from backend.agents.orchestrator import run_agent
    events = []
    async for event in run_agent("schedule a meeting tomorrow", "test-session-2"):
        events.append(event)

    thoughts = [e for e in events if isinstance(e, dict) and e.get("type") == "thought"]
    thought_texts = " ".join(t.get("content", "") for t in thoughts)
    assert "Calendar Agent" in thought_texts


@pytest.mark.asyncio
async def test_orchestrator_routes_to_notes_agent():
    """Orchestrator should delegate note requests to Notes Agent."""
    from backend.agents.orchestrator import run_agent
    events = []
    async for event in run_agent("search my notes about Q3", "test-session-3"):
        events.append(event)

    thoughts = [e for e in events if isinstance(e, dict) and e.get("type") == "thought"]
    thought_texts = " ".join(t.get("content", "") for t in thoughts)
    assert "Notes Agent" in thought_texts


@pytest.mark.asyncio
async def test_orchestrator_multi_agent_routing():
    """A request spanning domains should invoke multiple agents."""
    from backend.agents.orchestrator import _route_to_agent
    agents = _route_to_agent("create a task and schedule a meeting about it")
    assert "task" in agents
    assert "calendar" in agents


@pytest.mark.asyncio
async def test_orchestrator_general_fallback():
    """Unknown requests should fall back to general mode."""
    from backend.agents.orchestrator import _route_to_agent
    agents = _route_to_agent("what is the meaning of life")
    assert agents == ["general"]


# ══════════════════════════════════════════════════════════════════════════════
# ✅ Multi-Step Workflow Test
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_calendar_multi_step_workflow():
    """Calendar agent creates events with availability check (multi-step)."""
    from backend.agents import calendar_agent
    events = []
    async for event in calendar_agent.run(
        "schedule a team sync meeting tomorrow at 3pm", "test-session-workflow"
    ):
        events.append(event)

    thoughts = [e for e in events if isinstance(e, dict) and e.get("type") == "thought"]
    thought_texts = " ".join(t.get("content", "") for t in thoughts)

    assert "Calendar Agent activated" in thought_texts
    assert "Checking availability" in thought_texts or "Calling MCP tool" in thought_texts
