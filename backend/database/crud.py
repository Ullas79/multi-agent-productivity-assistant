"""
backend/database/crud.py – Full CRUD operations for all AgentFlow models.

Optimised for AlloyDB with proper type annotations and boolean filters.
"""
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc, desc, or_

from backend.database.models import Task, CalendarEvent, Note, AgentMemory, HAS_PGVECTOR

logger = logging.getLogger(__name__)

# ── Embedding helper (lazy-loaded) ────────────────────────────────────────────

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from vertexai.language_models import TextEmbeddingModel
            _embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        except Exception as e:
            logger.warning("Vertex AI embedding model unavailable: %s", e)
    return _embedding_model


async def _generate_embedding(text: str) -> Optional[list]:
    """Generate a vector embedding via Vertex AI (runs sync call in thread pool)."""
    model = _get_embedding_model()
    if model is None:
        return None
    try:
        embeddings = await asyncio.to_thread(model.get_embeddings, [text])
        return embeddings[0].values
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        return None


# ── Agent Memory ──────────────────────────────────────────────────────────────

async def save_memory(
    db: AsyncSession, session_id: str, role: str, content: str, agent_name: str = None
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
    stmt = (
        select(AgentMemory)
        .where(AgentMemory.session_id == session_id)
        .order_by(asc(AgentMemory.created_at))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ── Tasks ─────────────────────────────────────────────────────────────────────

async def create_task(
    db: AsyncSession, title: str, description: str = "",
    priority: str = "medium", due_date: str = None, tags: list = None,
) -> Task:
    parsed_due = None
    if due_date:
        try:
            parsed_due = datetime.fromisoformat(due_date)
        except ValueError:
            pass
    task = Task(
        id=str(uuid.uuid4()), title=title, description=description,
        priority=priority, due_date=parsed_due, tags=tags or [],
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_tasks(
    db: AsyncSession, status: str = None, priority: str = None, limit: int = 50,
) -> List[Task]:
    stmt = select(Task)
    if status:
        stmt = stmt.where(Task.status == status)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    stmt = stmt.order_by(desc(Task.created_at)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_task(db: AsyncSession, task_id: str) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def update_task(db: AsyncSession, task_id: str, **updates) -> Optional[Task]:
    task = await get_task(db, task_id)
    if not task:
        return None
    for key, value in updates.items():
        if key == "due_date" and isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                pass
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


# ── Calendar Events ───────────────────────────────────────────────────────────

async def create_event(
    db: AsyncSession, title: str, start_time: str, end_time: str,
    description: str = "", location: str = "", attendees: list = None,
) -> CalendarEvent:
    event = CalendarEvent(
        id=str(uuid.uuid4()), title=title, description=description,
        start_time=datetime.fromisoformat(start_time),
        end_time=datetime.fromisoformat(end_time),
        location=location, attendees=attendees or [],
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def get_events(
    db: AsyncSession, start_from: str = None, start_until: str = None, limit: int = 50,
) -> List[CalendarEvent]:
    stmt = select(CalendarEvent)
    if start_from:
        try:
            stmt = stmt.where(CalendarEvent.start_time >= datetime.fromisoformat(start_from))
        except ValueError:
            pass
    if start_until:
        try:
            stmt = stmt.where(CalendarEvent.start_time <= datetime.fromisoformat(start_until))
        except ValueError:
            pass
    stmt = stmt.order_by(asc(CalendarEvent.start_time)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_event(db: AsyncSession, event_id: str) -> Optional[CalendarEvent]:
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    return result.scalar_one_or_none()


async def update_event(db: AsyncSession, event_id: str, **updates) -> Optional[CalendarEvent]:
    event = await get_event(db, event_id)
    if not event:
        return None
    for key, value in updates.items():
        if key in ("start_time", "end_time") and isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                pass
        setattr(event, key, value)
    event.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, event_id: str) -> bool:
    event = await get_event(db, event_id)
    if not event:
        return False
    await db.delete(event)
    await db.flush()
    return True


# ── Notes ─────────────────────────────────────────────────────────────────────

async def create_note(
    db: AsyncSession, title: str, content: str,
    tags: list = None, is_pinned: bool = False,
) -> Note:
    note_data = dict(
        id=str(uuid.uuid4()), title=title, content=content,
        tags=tags or [], is_pinned=is_pinned,
    )
    # Generate embedding if pgvector is available
    if HAS_PGVECTOR:
        text_to_embed = f"Title: {title}\n\nContent: {content}"
        vector = await _generate_embedding(text_to_embed)
        if vector is not None:
            note_data["embedding"] = vector

    note = Note(**note_data)
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


async def get_notes(
    db: AsyncSession, pinned_only: bool = False, search: str = None, limit: int = 50,
) -> List[Note]:
    stmt = select(Note)
    if pinned_only:
        stmt = stmt.where(Note.is_pinned.is_(True))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Note.title.ilike(pattern), Note.content.ilike(pattern))
        )
    stmt = stmt.order_by(desc(Note.created_at)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_note(db: AsyncSession, note_id: str) -> Optional[Note]:
    result = await db.execute(select(Note).where(Note.id == note_id))
    return result.scalar_one_or_none()


async def update_note(db: AsyncSession, note_id: str, **updates) -> Optional[Note]:
    note = await get_note(db, note_id)
    if not note:
        return None
    for key, value in updates.items():
        setattr(note, key, value)
    note.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, note_id: str) -> bool:
    note = await get_note(db, note_id)
    if not note:
        return False
    await db.delete(note)
    await db.flush()
    return True


async def semantic_search_notes(db: AsyncSession, query: str, limit: int = 5) -> List[Note]:
    """Perform cosine similarity search on notes (requires pgvector on AlloyDB)."""
    if not HAS_PGVECTOR or not hasattr(Note, "embedding"):
        logger.warning("Semantic search unavailable: pgvector not installed.")
        return []
    query_vector = await _generate_embedding(query)
    if query_vector is None:
        return []
    stmt = (
        select(Note)
        .order_by(Note.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
