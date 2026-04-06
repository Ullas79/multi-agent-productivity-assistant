"""
AgentFlow – FastAPI Application (v2)
Endpoints:
  POST /api/chat          – SSE streaming chat with orchestrator
  WS   /ws/chat/{sid}     – WebSocket chat alternative
  GET  /api/sessions/{id}/history – Conversation history
  CRUD /api/tasks         – Task management
  CRUD /api/events        – Calendar event management
  CRUD /api/notes         – Notes management
  GET  /api/health        – Health check
  GET  /docs              – Swagger UI
  GET  /                  – Serves frontend SPA
"""
import uuid
import logging
import json
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.connection import init_db, close_db, get_db, AsyncSessionLocal
from backend.database import crud
from backend.agents.orchestrator import run_agent
from backend.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from backend.exceptions import register_exception_handlers
from backend.schemas import (
    ChatRequest,
    TaskCreate, TaskUpdate,
    EventCreate, EventUpdate,
    NoteCreate, NoteUpdate,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgentFlow starting up – initialising database...")
    await init_db()
    logger.info("AgentFlow ready!")
    yield
    await close_db()
    logger.info("AgentFlow shut down cleanly")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AgentFlow API",
    version=settings.app_version,
    description=(
        "Multi-Agent AI System for task, schedule, and information management. "
        "Powered by Gemini 2.0 Flash + Google ADK + MCP + AlloyDB."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register custom exception handlers
register_exception_handlers(app)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": settings.gemini_model,
        "agents": ["orchestrator", "task_manager", "calendar", "notes", "research"],
    }


# ── Chat – SSE Streaming ──────────────────────────────────────────────────────

@app.post("/api/chat", tags=["Chat"])
async def chat_sse(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    session_id = req.session_id or str(uuid.uuid4())

    # Persist user message
    await crud.save_memory(db, session_id, "user", req.message)

    async def event_stream():
        full_response = ""
        try:
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
            async for chunk in run_agent(req.message, session_id):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "text":
                        full_response += chunk.get("content", "")
                    yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        # Persist assistant response in a fresh session to avoid scope issues
        if full_response:
            try:
                async with AsyncSessionLocal() as save_db:
                    await crud.save_memory(
                        save_db, session_id, "assistant", full_response, "orchestrator"
                    )
                    await save_db.commit()
            except Exception as e:
                logger.error(f"Failed to persist assistant response: {e}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── WebSocket Chat ────────────────────────────────────────────────────────────

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            user_message = msg.get("message", "")

            # Persist user message
            async with AsyncSessionLocal() as db:
                await crud.save_memory(db, session_id, "user", user_message)
                await db.commit()

            await websocket.send_json({"type": "thinking", "content": "Processing..."})

            full_response = ""
            async for chunk in run_agent(user_message, session_id):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "text":
                        full_response += chunk.get("content", "")
                    await websocket.send_json(chunk)
                else:
                    full_response += chunk
                    await websocket.send_json({"type": "text", "content": chunk})

            await websocket.send_json({"type": "done", "content": full_response})

            # Persist assistant response
            if full_response:
                async with AsyncSessionLocal() as db:
                    await crud.save_memory(
                        db, session_id, "assistant", full_response, "orchestrator"
                    )
                    await db.commit()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")


# ── Session History ───────────────────────────────────────────────────────────

@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    memories = await crud.get_memory(db, session_id)
    return {"session_id": session_id, "messages": [m.to_dict() for m in memories]}


# ── Tasks API ─────────────────────────────────────────────────────────────────

@app.get("/api/tasks")
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    tasks = await crud.get_tasks(db, status=status, priority=priority, limit=limit)
    return {"tasks": [t.to_dict() for t in tasks], "count": len(tasks)}


@app.post("/api/tasks", status_code=201)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = await crud.create_task(
        db, title=body.title, description=body.description,
        priority=body.priority, due_date=body.due_date, tags=body.tags,
    )
    return task.to_dict()


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, body: TaskUpdate, db: AsyncSession = Depends(get_db)):
    updates = body.model_dump(exclude_none=True)
    task = await crud.update_task(db, task_id, **updates)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


# ── Calendar API ──────────────────────────────────────────────────────────────

@app.get("/api/events")
async def list_events(
    start_from: Optional[str] = Query(None),
    start_until: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    events = await crud.get_events(db, start_from=start_from, start_until=start_until, limit=limit)
    return {"events": [e.to_dict() for e in events], "count": len(events)}


@app.post("/api/events", status_code=201)
async def create_event(body: EventCreate, db: AsyncSession = Depends(get_db)):
    event = await crud.create_event(
        db, title=body.title, start_time=body.start_time,
        end_time=body.end_time, description=body.description,
        location=body.location, attendees=body.attendees,
    )
    return event.to_dict()


@app.get("/api/events/{event_id}")
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


@app.put("/api/events/{event_id}")
async def update_event(event_id: str, body: EventUpdate, db: AsyncSession = Depends(get_db)):
    updates = body.model_dump(exclude_none=True)
    event = await crud.update_event(db, event_id, **updates)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_event(db, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"success": True}


# ── Notes API ─────────────────────────────────────────────────────────────────

@app.get("/api/notes")
async def list_notes(
    pinned_only: bool = Query(False),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    notes = await crud.get_notes(db, pinned_only=pinned_only, search=search, limit=limit)
    return {"notes": [n.to_dict() for n in notes], "count": len(notes)}


@app.post("/api/notes", status_code=201)
async def create_note(body: NoteCreate, db: AsyncSession = Depends(get_db)):
    note = await crud.create_note(
        db, title=body.title, content=body.content,
        tags=body.tags, is_pinned=body.is_pinned,
    )
    return note.to_dict()


@app.get("/api/notes/{note_id}")
async def get_note(note_id: str, db: AsyncSession = Depends(get_db)):
    note = await crud.get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.to_dict()


@app.put("/api/notes/{note_id}")
async def update_note(note_id: str, body: NoteUpdate, db: AsyncSession = Depends(get_db)):
    updates = body.model_dump(exclude_none=True)
    note = await crud.update_note(db, note_id, **updates)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.to_dict()


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_note(db, note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"success": True}


# ── Frontend SPA ──────────────────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa(full_path: str = ""):
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        raise HTTPException(status_code=404)
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text())
    return HTMLResponse(
        "<h1>AgentFlow API</h1><p>Frontend not found. Visit /docs for the API.</p>"
    )
