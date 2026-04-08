"""
backend/database/crud.py – HMS CRUD operations.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import asc, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    HAS_PGVECTOR,
    AgentMemory,
    Appointment,
    ClinicalTask,
    PatientRecord,
)
from backend.config import settings

try:
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    HAS_VERTEX = True
except ImportError:
    HAS_VERTEX = False

logger = logging.getLogger(__name__)


# ── Agent Memory ──────────────────────────────────────────────────────────────
async def save_memory(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    agent_name: str = None,
) -> AgentMemory:
    mem = AgentMemory(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role=role,
        content=content,
        agent_name=agent_name,
    )
    db.add(mem)
    await db.flush()
    return mem


async def get_memory(db: AsyncSession, session_id: str) -> List[AgentMemory]:
    result = await db.execute(
        select(AgentMemory)
        .where(AgentMemory.session_id == session_id)
        .order_by(asc(AgentMemory.created_at))
    )
    return result.scalars().all()


# ── Clinical Tasks ────────────────────────────────────────────────────────────
async def create_task(
    db: AsyncSession,
    title: str,
    patient_name: str = None,
    description: str = "",
    priority: str = "medium",
    due_date: str = None,
    tags: list = None,
) -> ClinicalTask:
    parsed_due = datetime.fromisoformat(due_date) if due_date else None
    task = ClinicalTask(
        id=str(uuid.uuid4()),
        title=title,
        patient_name=patient_name,
        description=description,
        priority=priority,
        due_date=parsed_due,
        tags=tags or [],
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_tasks(
    db: AsyncSession,
    status: str = None,
    priority: str = None,
    limit: int = 50,
) -> List[ClinicalTask]:
    stmt = select(ClinicalTask)
    if status:
        stmt = stmt.where(ClinicalTask.status == status)
    if priority:
        stmt = stmt.where(ClinicalTask.priority == priority)

    result = await db.execute(stmt.order_by(desc(ClinicalTask.created_at)).limit(limit))
    return result.scalars().all()


async def get_task(db: AsyncSession, task_id: str) -> Optional[ClinicalTask]:
    return (
        await db.execute(select(ClinicalTask).where(ClinicalTask.id == task_id))
    ).scalar_one_or_none()


async def update_task(
    db: AsyncSession,
    task_id: str,
    **updates,
) -> Optional[ClinicalTask]:
    task = await get_task(db, task_id)
    if not task:
        return None

    for key, value in updates.items():
        if key == "due_date" and isinstance(value, str):
            value = datetime.fromisoformat(value)
        setattr(task, key, value)

    if updates.get("status") == "done" and task.completed_at is None:
        task.completed_at = datetime.now(timezone.utc)

    task.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: str) -> bool:
    task = await get_task(db, task_id)
    if not task:
        return False
    await db.delete(task)
    await db.flush()
    return True


# ── Appointments ──────────────────────────────────────────────────────────────
async def create_event(
    db: AsyncSession,
    patient_name: str,
    doctor_name: str,
    start_time: str,
    end_time: str,
    reason: str = "",
    location: str = "",
) -> Appointment:
    appt = Appointment(
        id=str(uuid.uuid4()),
        patient_name=patient_name,
        doctor_name=doctor_name,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        reason=reason,
        location=location,
    )
    db.add(appt)
    await db.flush()
    await db.refresh(appt)
    return appt


async def get_events(
    db: AsyncSession,
    start_from: str = None,
    start_until: str = None,
    limit: int = 50,
) -> List[Appointment]:
    stmt = select(Appointment)
    if start_from:
        stmt = stmt.where(Appointment.start_time >= datetime.fromisoformat(start_from.replace(" ", "+")))
    if start_until:
        stmt = stmt.where(Appointment.start_time <= datetime.fromisoformat(start_until.replace(" ", "+")))

    result = await db.execute(stmt.order_by(asc(Appointment.start_time)).limit(limit))
    return result.scalars().all()


async def get_event(db: AsyncSession, event_id: str) -> Optional[Appointment]:
    return (
        await db.execute(select(Appointment).where(Appointment.id == event_id))
    ).scalar_one_or_none()


async def update_event(
    db: AsyncSession,
    event_id: str,
    **updates,
) -> Optional[Appointment]:
    appt = await get_event(db, event_id)
    if not appt:
        return None

    for key, value in updates.items():
        if key in ("start_time", "end_time") and isinstance(value, str):
            value = datetime.fromisoformat(value)
        setattr(appt, key, value)

    appt.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(appt)
    return appt


async def delete_event(db: AsyncSession, event_id: str) -> bool:
    appt = await get_event(db, event_id)
    if not appt:
        return False
    await db.delete(appt)
    await db.flush()
    return True


# ── Patient Records (EHR) ─────────────────────────────────────────────────────
async def get_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using Vertex AI text-embedding-004."""
    if not HAS_VERTEX or not text:
        return None
    try:
        # Note: This is a synchronous call in the SDK, so we run it in a thread
        import asyncio
        from functools import partial

        def _fetch():
            model = TextEmbeddingModel.from_pretrained(settings.embedding_model)
            embeddings = model.get_embeddings([text])
            return embeddings[0].values

        return await asyncio.get_event_loop().run_in_executor(None, _fetch)
    except Exception as e:
        logger.warning(f"Failed to generate embedding: {e}")
        return None


async def create_note(
    db: AsyncSession,
    patient_name: str,
    content: str,
    tags: list = None,
    is_pinned: bool = False,
) -> PatientRecord:
    # Generate embedding for the content
    embedding = await get_embedding(content)

    record = PatientRecord(
        id=str(uuid.uuid4()),
        patient_name=patient_name,
        content=content,
        tags=tags or [],
        is_pinned=is_pinned,
        embedding=embedding if HAS_PGVECTOR else None,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def get_notes(
    db: AsyncSession,
    pinned_only: bool = False,
    search: str = None,
    limit: int = 50,
) -> List[PatientRecord]:
    stmt = select(PatientRecord)
    if pinned_only:
        stmt = stmt.where(PatientRecord.is_pinned.is_(True))
    if search:
        stmt = stmt.where(
            or_(
                PatientRecord.patient_name.ilike(f"%{search}%"),
                PatientRecord.content.ilike(f"%{search}%"),
            )
        )

    result = await db.execute(
        stmt.order_by(desc(PatientRecord.created_at)).limit(limit)
    )
    return result.scalars().all()


async def get_note(db: AsyncSession, note_id: str) -> Optional[PatientRecord]:
    return (
        await db.execute(select(PatientRecord).where(PatientRecord.id == note_id))
    ).scalar_one_or_none()


async def update_note(
    db: AsyncSession,
    note_id: str,
    **updates,
) -> Optional[PatientRecord]:
    record = await get_note(db, note_id)
    if not record:
        return None

    for key, value in updates.items():
        setattr(record, key, value)

    record.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(record)
    return record


async def delete_note(db: AsyncSession, note_id: str) -> bool:
    record = await get_note(db, note_id)
    if not record:
        return False
    await db.delete(record)
    await db.flush()
    return True


async def semantic_search_notes(
    db: AsyncSession,
    query: str,
    limit: int = 3,
) -> List[PatientRecord]:
    """Perform semantic search using pgvector and Vertex AI."""
    if not HAS_PGVECTOR:
        logger.warning("pgvector not available - falling back to text search")
        return await get_notes(db, search=query, limit=limit)

    query_embedding = await get_embedding(query)
    if not query_embedding:
        logger.warning("Failed to get query embedding - falling back to text search")
        return await get_notes(db, search=query, limit=limit)

    # Use pgvector distance operator <-> (L2 distance) or <=> (Cosine distance)
    # AlloyDB supports both. We'll use L2 for simplicity as it's common.
    stmt = (
        select(PatientRecord)
        .order_by(PatientRecord.embedding.l2_distance(query_embedding))
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    return result.scalars().all()
