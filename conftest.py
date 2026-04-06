"""
conftest.py – Shared pytest fixtures for AgentFlow test suite.
Uses an in-memory SQLite DB so no real Postgres is needed for CI.
"""
import os
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

# ── Set environment variables BEFORE any app import ──────────────────────────
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_REGION", "us-central1")
os.environ.setdefault("GOOGLE_API_KEY", "dummy-api-key")

# Override DB URL to in-memory SQLite before any app import
import backend.database.connection as _conn
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from backend.database.models import Base

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

# Monkey-patch connection module before app loads
_conn.engine = _test_engine
_conn.AsyncSessionLocal = _TestSession
_conn._initialised = True


async def _override_get_db():
    async with _TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Now import app (will use patched engine)
from backend.main import app
from backend.database.connection import get_db
app.dependency_overrides[get_db] = _override_get_db


# ── Mock the AI agent so tests don't call Gemini ────────────────────────────
async def _fake_agent(message: str, session_id: str):
    """Yield a fake streamed response."""
    yield f"I received your message: '{message}'. This is a test response."


@pytest.fixture(autouse=True, scope="session")
def mock_agent():
    with patch("backend.main.run_agent", side_effect=_fake_agent):
        yield


# ── Event loop (session-scoped) ───────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ── DB setup ─────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables in the in-memory DB once per test session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── HTTP client ───────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


# ── Convenience fixtures ───────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def sample_task(client):
    """Create and return a sample task for use in tests."""
    resp = await client.post("/api/clinical-tasks", json={
        "title": "Sample Task",
        "description": "Created by fixture",
        "patient_name": "Test Patient",
        "priority": "medium",
        "tags": ["fixture", "test"],
    })
    return resp.json()


@pytest_asyncio.fixture
async def sample_event(client):
    """Create and return a sample calendar appointment."""
    from datetime import datetime, timedelta, timezone
    start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
    resp = await client.post("/api/appointments", json={
        "patient_name": "Test Patient",
        "doctor_name": "Dr. Test",
        "reason": "Routine Checkup",
        "start_time": start,
        "end_time": end,
        "location": "Zoom",
    })
    return resp.json()


@pytest_asyncio.fixture
async def sample_note(client):
    """Create and return a sample patient record."""
    resp = await client.post("/api/patient-records", json={
        "patient_name": "Test Patient",
        "content": "This is sample note content created by a fixture.",
        "tags": ["fixture"],
    })
    return resp.json()
