"""
AgentFlow HMS – FastAPI Application
Endpoints:
  POST /api/chat               – SSE streaming chat with medical orchestrator
  GET  /api/sessions/{id}/history – Conversation history
  CRUD /api/clinical-tasks     – Clinical Task management
  CRUD /api/appointments       – Doctor Appointment management
  CRUD /api/patient-records    – EHR Notes management
  GET  /api/health             – Health check
  GET  /docs                   – Swagger UI
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.orchestrator import run_agent
from backend.config import get_settings
from backend.database import crud
from backend.database.connection import close_db, get_db, get_session_factory, init_db
from backend.exceptions import register_exception_handlers
from backend.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from backend.schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    ChatRequest,
    ClinicalTaskCreate,
    ClinicalTaskUpdate,
    PatientRecordCreate,
    PatientRecordUpdate,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgentFlow HMS starting up – initialising database...")
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="AgentFlow Hospital Management System API",
    version=settings.app_version,
    description="Multi-Agent AI System for clinical tasks, appointments, and patient records.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

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


@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": "AgentFlow HMS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": settings.gemini_model,
    }


# ── Chat – SSE Streaming ──────────────────────────────────────────────────────
@app.post("/api/chat", tags=["AI Orchestrator"])
async def chat_sse(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    session_id = req.session_id or str(uuid.uuid4())
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

        if full_response:
            try:
                SessionFactory = get_session_factory()
                async with SessionFactory() as save_db:
                    await crud.save_memory(
                        save_db, session_id, "assistant", full_response, "orchestrator"
                    )
                    await save_db.commit()
            except Exception as e:
                logger.error(f"Failed to persist assistant response: {e}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sessions/{session_id}/history", tags=["AI Orchestrator"])
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    memories = await crud.get_memory(db, session_id)
    return {"session_id": session_id, "messages": [m.to_dict() for m in memories]}


# ── Clinical Tasks API ────────────────────────────────────────────────────────
@app.get("/api/clinical-tasks", tags=["Clinical Tasks"])
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
):
    tasks = await crud.get_tasks(db, status=status, priority=priority, limit=limit)
    return {"tasks": [t.to_dict() for t in tasks], "count": len(tasks)}


@app.get("/api/clinical-tasks/{task_id}", tags=["Clinical Tasks"])
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.post("/api/clinical-tasks", status_code=201, tags=["Clinical Tasks"])
async def create_task(body: ClinicalTaskCreate, db: AsyncSession = Depends(get_db)):
    task = await crud.create_task(
        db,
        title=body.title,
        patient_name=body.patient_name,
        description=body.description,
        priority=body.priority,
        due_date=body.due_date,
        tags=body.tags,
    )
    await db.commit()
    return task.to_dict()


@app.put("/api/clinical-tasks/{task_id}", tags=["Clinical Tasks"])
async def update_task(
    task_id: str, body: ClinicalTaskUpdate, db: AsyncSession = Depends(get_db)
):
    task = await crud.update_task(db, task_id, **body.model_dump(exclude_none=True))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.commit()
    return task.to_dict()


@app.delete("/api/clinical-tasks/{task_id}", tags=["Clinical Tasks"])
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    if not await crud.delete_task(db, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    await db.commit()
    return {"success": True}


# ── Appointments API ──────────────────────────────────────────────────────────
@app.get("/api/appointments", tags=["Appointments"])
async def list_events(
    start_from: Optional[str] = Query(None),
    start_until: Optional[str] = Query(None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
):
    events = await crud.get_events(
        db, start_from=start_from, start_until=start_until, limit=limit
    )
    return {"events": [e.to_dict() for e in events], "count": len(events)}


@app.get("/api/appointments/{event_id}", tags=["Appointments"])
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await crud.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return event.to_dict()


@app.post("/api/appointments", status_code=201, tags=["Appointments"])
async def create_event(body: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    event = await crud.create_event(
        db,
        patient_name=body.patient_name,
        doctor_name=body.doctor_name,
        start_time=body.start_time,
        end_time=body.end_time,
        reason=body.reason,
        location=body.location,
    )
    await db.commit()
    return event.to_dict()


@app.put("/api/appointments/{event_id}", tags=["Appointments"])
async def update_event(
    event_id: str, body: AppointmentUpdate, db: AsyncSession = Depends(get_db)
):
    event = await crud.update_event(db, event_id, **body.model_dump(exclude_none=True))
    if not event:
        raise HTTPException(status_code=404, detail="Appointment not found")
    await db.commit()
    return event.to_dict()


@app.delete("/api/appointments/{event_id}", tags=["Appointments"])
async def delete_event(event_id: str, db: AsyncSession = Depends(get_db)):
    if not await crud.delete_event(db, event_id):
        raise HTTPException(status_code=404, detail="Appointment not found")
    await db.commit()
    return {"success": True}


# ── Patient Records (EHR) API ────────────────────────────────────────────────
@app.get("/api/patient-records", tags=["Patient Records"])
async def list_notes(
    pinned_only: bool = Query(False),
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
):
    notes = await crud.get_notes(
        db, pinned_only=pinned_only, search=search, limit=limit
    )
    return {"notes": [n.to_dict() for n in notes], "count": len(notes)}


@app.get("/api/patient-records/{note_id}", tags=["Patient Records"])
async def get_note(note_id: str, db: AsyncSession = Depends(get_db)):
    note = await crud.get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Record not found")
    return note.to_dict()


@app.post("/api/patient-records", status_code=201, tags=["Patient Records"])
async def create_note(body: PatientRecordCreate, db: AsyncSession = Depends(get_db)):
    note = await crud.create_note(
        db,
        patient_name=body.patient_name,
        content=body.content,
        tags=body.tags,
        is_pinned=body.is_pinned,
    )
    await db.commit()
    return note.to_dict()


@app.put("/api/patient-records/{note_id}", tags=["Patient Records"])
async def update_note(
    note_id: str, body: PatientRecordUpdate, db: AsyncSession = Depends(get_db)
):
    note = await crud.update_note(db, note_id, **body.model_dump(exclude_none=True))
    if not note:
        raise HTTPException(status_code=404, detail="Record not found")
    await db.commit()
    return note.to_dict()


@app.delete("/api/patient-records/{note_id}", tags=["Patient Records"])
async def delete_note(note_id: str, db: AsyncSession = Depends(get_db)):
    if not await crud.delete_note(db, note_id):
        raise HTTPException(status_code=404, detail="Record not found")
    await db.commit()
    return {"success": True}
