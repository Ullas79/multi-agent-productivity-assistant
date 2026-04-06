"""
test_agents.py – Tests for agent endpoint, session handling,
and multi-turn conversation flow.
"""
import pytest
import json


@pytest.mark.asyncio
async def test_chat_returns_sse_stream(client):
    """POST /api/chat should stream SSE events."""
    resp = await client.post(
        "/api/chat",
        json={"message": "Hello, list my tasks"},
        headers={"Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    body = resp.text
    assert "data:" in body  # SSE format


@pytest.mark.asyncio
async def test_chat_returns_session_id(client):
    """Response stream should include a session_id event."""
    resp = await client.post("/api/chat", json={"message": "hi"})
    body = resp.text
    session_ids = [
        line for line in body.split("\n")
        if "session_id" in line and line.startswith("data:")
    ]
    assert len(session_ids) >= 1
    payload = json.loads(session_ids[0].replace("data: ", ""))
    assert "session_id" in payload


@pytest.mark.asyncio
async def test_chat_with_explicit_session(client):
    """Providing a session_id keeps conversation context."""
    sid = "test-session-abc123"
    resp = await client.post(
        "/api/chat",
        json={"message": "Remember this session", "session_id": sid},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_session_history(client):
    """After chatting, history endpoint should return messages."""
    sid = "history-test-session"
    await client.post("/api/chat", json={"message": "hello", "session_id": sid})

    resp = await client.get(f"/api/sessions/{sid}/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "messages" in data
    assert data["session_id"] == sid


@pytest.mark.asyncio
async def test_health_includes_model(client):
    """Health check should expose the Gemini model name."""
    resp = await client.get("/api/health")
    data = resp.json()
    assert "model" in data
    assert "gemini" in data["model"].lower()


@pytest.mark.asyncio
async def test_task_full_lifecycle(client, sample_task):
    """Create → Read → Update status → Verify done → Delete."""
    task_id = sample_task["id"]

    # Read
    resp = await client.get(f"/api/clinical-tasks/{task_id}")
    assert resp.json()["title"] == "Sample Task"

    # Mark in_progress
    resp = await client.put(f"/api/clinical-tasks/{task_id}", json={"status": "in_progress"})
    assert resp.json()["status"] == "in_progress"

    # Mark done
    resp = await client.put(f"/api/clinical-tasks/{task_id}", json={"status": "done"})
    assert resp.json()["status"] == "done"
    assert resp.json()["completed_at"] is not None  # timestamp set

    # Delete
    resp = await client.delete(f"/api/clinical-tasks/{task_id}")
    assert resp.json()["success"] is True

    # Confirm gone
    resp = await client.get(f"/api/clinical-tasks/{task_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_event_full_lifecycle(client, sample_event):
    """Create → Read → Update location → Delete."""
    eid = sample_event["id"]

    resp = await client.get(f"/api/appointments/{eid}")
    assert resp.json()["patient_name"] == "Test Patient"

    resp = await client.put(f"/api/appointments/{eid}", json={"location": "Google Meet"})
    assert resp.json()["location"] == "Google Meet"

    resp = await client.delete(f"/api/appointments/{eid}")
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_note_full_lifecycle(client, sample_note):
    """Create → Read → Pin → Search → Delete."""
    nid = sample_note["id"]

    resp = await client.get(f"/api/patient-records/{nid}")
    assert resp.json()["patient_name"] == "Test Patient"

    # Pin the note
    resp = await client.put(f"/api/patient-records/{nid}", json={"is_pinned": True})
    assert resp.json()["is_pinned"] is True

    # Should appear in pinned list
    resp = await client.get("/api/patient-records?pinned_only=true")
    ids = [n["id"] for n in resp.json()["notes"]]
    assert nid in ids

    # Search
    resp = await client.get("/api/patient-records?search=sample+note+content")
    assert resp.json()["count"] >= 1

    # Delete
    resp = await client.delete(f"/api/patient-records/{nid}")
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_task_priority_filter(client):
    """Filter tasks by priority should only return matching tasks."""
    await client.post("/api/clinical-tasks", json={"title": "High P Task", "patient_name": "Test Patient", "priority": "high"})
    await client.post("/api/clinical-tasks", json={"title": "Low P Task", "patient_name": "Test Patient", "priority": "low"})

    resp = await client.get("/api/clinical-tasks?priority=high")
    tasks = resp.json()["tasks"]
    assert all(t["priority"] == "high" for t in tasks)


@pytest.mark.asyncio
async def test_events_date_filter(client):
    """Events filtered by start_from should exclude past events."""
    from datetime import datetime, timedelta, timezone

    # Create future event
    future = datetime.now(timezone.utc) + timedelta(days=10)
    await client.post("/api/appointments", json={
        "patient_name": "Future Event", "doctor_name": "Dr Test",
        "start_time": future.isoformat(),
        "end_time": (future + timedelta(hours=1)).isoformat(),
    })

    # Filter from tomorrow onwards
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = await client.get(f"/api/appointments?start_from={tomorrow}")
    assert resp.status_code == 200
    events = resp.json()["events"]
    assert all(e["start_time"] >= tomorrow for e in events)


@pytest.mark.asyncio
async def test_invalid_task_id_returns_404(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/clinical-tasks/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_missing_required_fields(client):
    """Creating a task without title should fail validation."""
    resp = await client.post("/api/clinical-tasks", json={"priority": "high"})
    assert resp.status_code == 422  # Unprocessable Entity
